# Modulus FastAPI JSON API layer
#
# This thin layer wraps the Modulus engine (modulus/*) as a JSON API and, in
# production, serves the built React frontend from the same service. FastAPI and
# uvicorn are declared under the optional "api" extra in pyproject.toml.
#
# Run locally (from the mechopt/ project directory):
#   uvicorn api:app --reload --port 8000   # API only; run the SPA via `npm run dev`
#   python api.py                          # convenience entry point (same server)
#
# Production (single service): build the frontend so ../frontend/build exists,
# then run `uvicorn api:app --host 0.0.0.0 --port $PORT`.

import io
import math
from typing import Any, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from modulus.materials import MATERIALS, Material
from modulus.sections import (
    rectangle, circle, i_beam, hollow_rectangle,
    square_tube, hollow_circle, SectionProps,
)
from modulus.beam import max_moment, max_stress, max_deflection, factor_of_safety
from modulus.optimizer import evaluate_candidates, recommend
from modulus.decision import (
    rank_candidates, pareto_front, knee_point,
    classify_infeasible, explain_winner,
)
from modulus.design_review import generate_review
from modulus.bracket import evaluate_bracket, compare_gussets, GUSSET_TYPES
from modulus.failure_modes import evaluate_candidate, CheckResult, SafetyCase, Status
from modulus.uncertainty import run_monte_carlo, reliability_summary
from modulus.envelope import evaluate_envelope
from modulus.stock import nearest_buyable, STOCK_DIMS_MM, BOLT_SIZES
from modulus.units import UnitSystem, convert_input, convert_output, unit_label, format_value
from modulus.report import export_report_bytes

# ---------------------------------------------------------------------------
# Section function registry
# ---------------------------------------------------------------------------

SECTION_FNS = {
    "rectangle":       rectangle,
    "circle":          circle,
    "i_beam":          i_beam,
    "hollow_rectangle": hollow_rectangle,
    "square_tube":     square_tube,
    "hollow_circle":   hollow_circle,
}

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Modulus API",
    description=(
        "JSON API layer over the Modulus mechanical design optimisation engine. "
        "All mechanics live in the engine modules — this file only wraps them."
    ),
    version="0.1.0",
)

# CORS: allow the React dev server on localhost:3000 to call localhost:8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# NaN / Inf-safe JSON encoder
# ---------------------------------------------------------------------------

def _clean(value: Any) -> Any:
    """Recursively replace float NaN/Inf with None so JSON serialises cleanly."""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    # numpy scalars
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _json_response(data: Any) -> JSONResponse:
    """Return a JSONResponse with NaN/Inf scrubbed to null."""
    return JSONResponse(content=_clean(data))


# ---------------------------------------------------------------------------
# SafetyCase serialisation helper
# ---------------------------------------------------------------------------

def _serialise_safety_case(sc: SafetyCase) -> dict:
    return {
        "checks": [
            {
                "name":      c.name,
                "actual":    _clean(c.actual),
                "allowable": _clean(c.allowable),
                "margin":    _clean(c.margin),
                "status":    c.status.value,
                "notes":     c.notes,
            }
            for c in sc.checks
        ],
        "overall_status":    sc.overall_status.value,
        "controlling_check": sc.controlling_check,
        "failure_reasons":   sc.failure_reasons,
    }


# ---------------------------------------------------------------------------
# DataFrame-to-records helper
# ---------------------------------------------------------------------------

def _df_to_records(df) -> list[dict]:
    """Convert the evaluated DataFrame to a JSON-safe list of dicts.

    The 'safety_case' column contains Python objects and is serialised
    separately; all other columns go through the NaN/Inf cleaner.
    """
    records = []
    has_sc = "safety_case" in df.columns
    for _, row in df.iterrows():
        rec: dict[str, Any] = {}
        for col in df.columns:
            if col == "safety_case":
                continue
            rec[col] = _clean(row[col])
        if has_sc and row.get("safety_case") is not None:
            rec["safety_case"] = _serialise_safety_case(row["safety_case"])
        records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Static file serving (React SPA)
# ---------------------------------------------------------------------------
# Mount only when the build directory exists; during development without a
# built frontend the API still operates normally.
import os as _os
_frontend_dir = _os.path.join(_os.path.dirname(__file__), "..", "frontend", "build")
# The built SPA is mounted at the very end of this file (after every /api route)
# so that the API always takes precedence over the static catch-all.


# ===========================================================================
# Pydantic request/response models
# ===========================================================================

# ---------------------------------------------------------------------------
# Beam endpoints
# ---------------------------------------------------------------------------

class BeamBaseRequest(BaseModel):
    load:              float = Field(..., description="Applied load [N]")
    length:            float = Field(..., description="Beam span [m]")
    load_case:         str   = Field(..., description="cantilever_end | cantilever_udl | simply_center | simply_udl")
    fos_target:        float = Field(1.5,  description="Minimum required factor of safety")
    material_keys:     Optional[list[str]]  = Field(None, description="Subset of MATERIALS keys to consider")
    section_types:     Optional[list[str]]  = Field(None, description="Subset of section types to consider")
    deflection_limit:  Optional[float]      = Field(None, description="Max allowable deflection [m]")
    stock_mode:        bool                 = Field(False, description="Restrict sweep to standard stock sizes")


class BeamEvaluateRequest(BeamBaseRequest):
    pass


class BeamRecommendRequest(BeamBaseRequest):
    priority: str = Field("balanced", description="lightest | cheapest | safest | balanced")


class BeamRankRequest(BeamBaseRequest):
    priority: str = Field("balanced")


class BeamParetoRequest(BeamBaseRequest):
    objectives: Optional[list[list[str]]] = Field(
        None,
        description='[["weight","min"],["cost","min"]] — list of [column, direction] pairs',
    )


class BeamDesignReviewRequest(BeamBaseRequest):
    priority:         str            = Field("balanced")
    deflection_limit: Optional[float] = Field(None)


class BeamMonteCarloRequest(BaseModel):
    material_key:  str   = Field(..., description="Key into MATERIALS dict")
    section_type:  str   = Field(..., description="Section type name")
    d_mm:          float = Field(..., description="Primary dimension [mm]")
    load:          float = Field(..., description="Applied load [N]")
    length:        float = Field(..., description="Beam span [m]")
    load_case:     str   = Field(...)
    fos_target:    float = Field(2.0)
    n_samples:     int   = Field(1000)
    load_cov:      float = Field(0.10)
    dimension_cov: float = Field(0.02)
    E_cov:         float = Field(0.05)
    sigma_y_cov:   float = Field(0.05)
    seed:          Optional[int] = Field(None)


class EnvelopeLoadCase(BaseModel):
    name:      str
    load:      float
    length:    float
    load_case: str


class BeamEnvelopeRequest(BaseModel):
    material_key:     str   = Field(...)
    section_type:     str   = Field(...)
    d_mm:             float = Field(...)
    load_cases:       list[EnvelopeLoadCase] = Field(...)
    fos_target:       float = Field(2.0)
    deflection_limit: Optional[float] = Field(None)


# ---------------------------------------------------------------------------
# Bracket endpoints
# ---------------------------------------------------------------------------

class BracketEvaluateRequest(BaseModel):
    P:                 float = Field(..., description="Load [N]")
    e:                 float = Field(..., description="Load offset from wall [m]")
    width:             float = Field(..., description="Plate width [m]")
    thickness:         float = Field(..., description="Plate thickness [m]")
    material_key:      str   = Field(...)
    fos_target:        float = Field(1.5)
    bolt_count:        int   = Field(...)
    bolt_diameter:     float = Field(..., description="Bolt shank diameter [m]")
    bolt_spacing_v:    float = Field(..., description="Vertical bolt spacing [m]")
    bolt_sigma_allow:  float = Field(640e6, description="Bolt allowable stress [Pa]")
    deflection_limit:  Optional[float] = Field(None)
    gusset_type:       str   = Field("none")
    gusset_depth:      float = Field(0.0)
    gusset_thickness:  Optional[float] = Field(None)
    edge_distance:     Optional[float] = Field(None)


class BracketCompareGussetsRequest(BaseModel):
    P:                float
    e:                float
    width:            float
    thickness:        float
    material_key:     str
    fos_target:       float = 1.5
    bolt_count:       int
    bolt_diameter:    float
    bolt_spacing_v:   float
    bolt_sigma_allow: float = 640e6
    deflection_limit: Optional[float] = None
    gusset_depth:     float = 0.05
    gusset_thickness: Optional[float] = None
    edge_distance:    Optional[float] = None


# ---------------------------------------------------------------------------
# Stock endpoint
# ---------------------------------------------------------------------------

class StockNearestRequest(BaseModel):
    material_key:     str
    section_type:     str
    dims_mm:          dict = Field(..., description="Dimension dict, e.g. {d_mm: 30}")
    load:             float
    length:           float
    load_case:        str
    fos_target:       float = 1.5
    deflection_limit: Optional[float] = None


# ---------------------------------------------------------------------------
# Export endpoint
# ---------------------------------------------------------------------------

class ExportRequest(BeamBaseRequest):
    priority:         str = Field("balanced")
    format:           str = Field("csv", description="csv | json | text | pdf")


# ===========================================================================
# Helper: run the standard beam sweep and return (df, winner)
# Centralises the evaluate → recommend call used by several endpoints.
# ===========================================================================

def _run_sweep(req: BeamBaseRequest):
    """Evaluate candidates and return the raw DataFrame."""
    return evaluate_candidates(
        load=req.load,
        length=req.length,
        load_case=req.load_case,
        fos_target=req.fos_target,
        material_keys=req.material_keys,
        section_types=req.section_types,
        deflection_limit=req.deflection_limit,
        stock_mode=req.stock_mode,
    )


# ===========================================================================
# GET endpoints — catalogue data
# ===========================================================================

@app.get("/api/materials")
def get_materials():
    """List all available materials with key properties."""
    return _json_response([
        {
            "key":     key,
            "name":    mat.name,
            "E":       mat.E,
            "sigma_y": mat.sigma_y,
            "rho":     mat.rho,
            "cost":    mat.cost,
        }
        for key, mat in MATERIALS.items()
    ])


@app.get("/api/sections")
def get_sections():
    """List all available section types with their parameter names."""
    section_params = {
        "rectangle":        [{"name": "b",  "label": "Width (m)"},
                             {"name": "h",  "label": "Height (m)"}],
        "circle":           [{"name": "d",  "label": "Diameter (m)"}],
        "i_beam":           [{"name": "b",  "label": "Flange Width (m)"},
                             {"name": "h",  "label": "Total Height (m)"},
                             {"name": "tf", "label": "Flange Thickness (m)"},
                             {"name": "tw", "label": "Web Thickness (m)"}],
        "hollow_rectangle": [{"name": "b",  "label": "Outer Width (m)"},
                             {"name": "h",  "label": "Outer Height (m)"},
                             {"name": "w",  "label": "Wall Thickness (m)"}],
        "square_tube":      [{"name": "a",  "label": "Outer Side (m)"},
                             {"name": "w",  "label": "Wall Thickness (m)"}],
        "hollow_circle":    [{"name": "d",  "label": "Outer Diameter (m)"},
                             {"name": "di", "label": "Inner Diameter (m)"}],
    }
    return _json_response([
        {"name": name, "params": params}
        for name, params in section_params.items()
    ])


@app.get("/api/load-cases")
def get_load_cases():
    """List all supported beam load cases."""
    return _json_response([
        {"key": "cantilever_end", "label": "Cantilever — point load at free end"},
        {"key": "cantilever_udl", "label": "Cantilever — uniformly distributed load"},
        {"key": "simply_center",  "label": "Simply supported — point load at mid-span"},
        {"key": "simply_udl",     "label": "Simply supported — uniformly distributed load"},
    ])


@app.get("/api/units/systems")
def get_unit_systems():
    """List all supported unit systems."""
    return _json_response([
        {"key": "si",       "label": "SI (m, N, Pa, kg)"},
        {"key": "mm",       "label": "MM (mm, N, MPa, kg)"},
        {"key": "imperial", "label": "Imperial (in, lbf, psi, lb)"},
    ])


# ===========================================================================
# POST — Beam: evaluate (full sweep, return all candidates)
# ===========================================================================

@app.post("/api/beam/evaluate")
def beam_evaluate(req: BeamEvaluateRequest):
    """
    Sweep design space and return every candidate with stress, deflection,
    FoS, weight, cost, safe flag, and a serialised SafetyCase.
    """
    try:
        df = _run_sweep(req)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    records = _df_to_records(df)
    return _json_response({
        "candidates": records,
        "count":      len(records),
        "safe_count": int(df["safe"].sum()),
    })


# ===========================================================================
# POST — Beam: recommend (single winner)
# ===========================================================================

@app.post("/api/beam/recommend")
def beam_recommend(req: BeamRecommendRequest):
    """
    Return the single recommended design plus a serialised SafetyCase.
    """
    try:
        df = _run_sweep(req)
        winner = recommend(df, priority=req.priority)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    winner_dict = {
        col: _clean(winner[col])
        for col in df.columns
        if col != "safety_case"
    }
    if "safety_case" in winner.index:
        winner_dict["safety_case"] = _serialise_safety_case(winner["safety_case"])

    return _json_response({
        "recommended": winner_dict,
        "safety_case": _serialise_safety_case(winner["safety_case"]),
    })


# ===========================================================================
# POST — Beam: rank (all safe, ranked by priority)
# ===========================================================================

@app.post("/api/beam/rank")
def beam_rank(req: BeamRankRequest):
    """
    Return all candidates ranked by priority.  Safe candidates get a numeric
    rank; infeasible rows get null rank plus a classified infeasibility reason.
    """
    try:
        df = _run_sweep(req)
        ranked_df = rank_candidates(df, priority=req.priority)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    infeasible_reasons = classify_infeasible(ranked_df)

    records = _df_to_records(ranked_df)
    # Attach infeasibility reason to each record
    for rec, reason in zip(records, infeasible_reasons.tolist()):
        rec["infeasibility_reason"] = reason

    # Build a summary dict {index_str: reason} for the infeasible subset
    infeasible_map: dict[str, str] = {}
    for idx, reason in infeasible_reasons.items():
        if reason != "feasible":
            infeasible_map[str(idx)] = reason

    return _json_response({
        "ranked":             records,
        "infeasible_reasons": infeasible_map,
    })


# ===========================================================================
# POST — Beam: Pareto front
# ===========================================================================

@app.post("/api/beam/pareto")
def beam_pareto(req: BeamParetoRequest):
    """
    Compute the Pareto-optimal front of safe candidates and return it together
    with the knee-point index.

    objectives format: [["weight","min"],["cost","min"]]
    """
    try:
        df = _run_sweep(req)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Parse objectives
    if req.objectives is not None:
        objectives = [tuple(pair) for pair in req.objectives]
    else:
        objectives = [("weight", "min"), ("cost", "min")]

    try:
        front_df = pareto_front(df, objectives=objectives)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if front_df.empty:
        return _json_response({"front": [], "knee_index": None, "knee_point": None})

    try:
        kp_idx = knee_point(front_df, objectives=objectives)
    except Exception:
        kp_idx = front_df.index[0]

    kp_row = front_df.loc[kp_idx]
    kp_dict = {col: _clean(kp_row[col]) for col in front_df.columns if col != "safety_case"}
    if "safety_case" in kp_row.index:
        kp_dict["safety_case"] = _serialise_safety_case(kp_row["safety_case"])

    front_records = _df_to_records(front_df)

    return _json_response({
        "front":       front_records,
        "knee_index":  int(kp_idx),
        "knee_point":  kp_dict,
    })


# ===========================================================================
# POST — Beam: design review (the "feels special" capstone endpoint)
# ===========================================================================

@app.post("/api/beam/design-review")
def beam_design_review(req: BeamDesignReviewRequest):
    """
    Run the full sweep, pick the winner, and return a structured design review:
    recommended design, why it won, controlling constraint, sensitivities,
    unmodelled risks, nearest alternative, and recommended next step.
    """
    try:
        df = _run_sweep(req)
        winner = recommend(df, priority=req.priority)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        review = generate_review(
            winner=winner,
            df=df,
            priority=req.priority,
            load=req.load,
            length=req.length,
            load_case=req.load_case,
            fos_target=req.fos_target,
            deflection_limit=req.deflection_limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Review generation failed: {exc}")

    # Serialise the recommended winner row
    winner_dict = {
        col: _clean(winner[col])
        for col in df.columns
        if col != "safety_case"
    }
    if "safety_case" in winner.index:
        winner_dict["safety_case"] = _serialise_safety_case(winner["safety_case"])

    sensitivities = [
        {
            "parameter":         s.parameter,
            "baseline_value":    _clean(s.baseline_value),
            "bumped_value":      _clean(s.bumped_value),
            "fos_change":        _clean(s.fos_change),
            "deflection_change": _clean(s.deflection_change),
        }
        for s in review.sensitivities
    ]

    return _json_response({
        "recommended":              winner_dict,
        "why_it_won":               review.why_it_won,
        "controlling_constraint":   review.controlling_constraint,
        "controlling_margin":       _clean(review.controlling_margin),
        "sensitivities":            sensitivities,
        "most_important_sensitivity": review.most_important_sensitivity,
        "unmodeled_risks":          review.unmodeled_risks,
        "nearest_alternative":      review.nearest_alternative,
        "recommended_next_step":    review.recommended_next_step,
    })


# ===========================================================================
# POST — Beam: Monte Carlo uncertainty analysis
# ===========================================================================

@app.post("/api/beam/monte-carlo")
def beam_monte_carlo(req: BeamMonteCarloRequest):
    """
    Run a Monte Carlo reliability simulation on a single design and return
    summary statistics plus a histogram of FoS samples.
    """
    try:
        result = run_monte_carlo(
            material_key=req.material_key,
            section_type=req.section_type,
            d_mm=req.d_mm,
            load=req.load,
            length=req.length,
            load_case=req.load_case,
            fos_target=req.fos_target,
            n_samples=req.n_samples,
            load_cov=req.load_cov,
            dimension_cov=req.dimension_cov,
            E_cov=req.E_cov,
            sigma_y_cov=req.sigma_y_cov,
            seed=req.seed,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Build histogram (30 bins) over the FoS samples
    fos_arr = result.samples["fos"]
    counts, bin_edges = np.histogram(fos_arr, bins=30)
    histogram = {
        "bins":   bin_edges.tolist(),   # len = 31 (left edges + right edge)
        "counts": counts.tolist(),
    }

    return _json_response({
        "n_samples":           result.n_samples,
        "fos_mean":            _clean(result.fos_mean),
        "fos_std":             _clean(result.fos_std),
        "fos_p5":              _clean(result.fos_p5),
        "fos_p95":             _clean(result.fos_p95),
        "failure_probability": _clean(result.failure_probability),
        "deflection_mean":     _clean(result.deflection_mean),
        "deflection_std":      _clean(result.deflection_std),
        "stress_mean":         _clean(result.stress_mean),
        "stress_std":          _clean(result.stress_std),
        "fos_histogram":       histogram,
    })


# ===========================================================================
# POST — Beam: load-case envelope analysis
# ===========================================================================

@app.post("/api/beam/envelope")
def beam_envelope(req: BeamEnvelopeRequest):
    """
    Evaluate one design under multiple load cases simultaneously and identify
    the governing (worst-case) load case.
    """
    load_cases_dicts = [lc.model_dump() for lc in req.load_cases]

    try:
        result = evaluate_envelope(
            material_key=req.material_key,
            section_type=req.section_type,
            d_mm=req.d_mm,
            load_cases=load_cases_dicts,
            fos_target=req.fos_target,
            deflection_limit=req.deflection_limit,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    cases = [
        {
            "load_case":   c.load_case,
            "load":        _clean(c.load),
            "length":      _clean(c.length),
            "stress":      _clean(c.stress),
            "deflection":  _clean(c.deflection),
            "fos":         _clean(c.fos),
        }
        for c in result.cases
    ]

    return _json_response({
        "cases":               cases,
        "governing_case":      result.governing_case,
        "governing_fos":       _clean(result.governing_fos),
        "governing_stress":    _clean(result.governing_stress),
        "governing_deflection": _clean(result.governing_deflection),
        "all_safe":            result.all_safe,
        "summary":             result.summary,
    })


# ===========================================================================
# POST — Bracket: single evaluation
# ===========================================================================

def _serialise_bracket_result(res) -> dict:
    """Convert a BracketResult dataclass to a JSON-safe dict."""
    bolt = res.bolt
    bolt_dict = {
        "shear_per_bolt":        _clean(bolt.shear_per_bolt),
        "max_tension":           _clean(bolt.max_tension),
        "bolt_area":             _clean(bolt.bolt_area),
        "shear_stress":          _clean(bolt.shear_stress),
        "tension_stress":        _clean(bolt.tension_stress),
        "combined_utilization":  _clean(bolt.combined_utilization),
        "bolt_fos":              _clean(bolt.bolt_fos),
        "bearing_stress":        _clean(bolt.bearing_stress),
        "bearing_fos":           _clean(bolt.bearing_fos),
        "tearout_stress":        _clean(bolt.tearout_stress),
        "tearout_fos":           _clean(bolt.tearout_fos),
        "edge_distance_ok":      bolt.edge_distance_ok,
        "warnings":              bolt.warnings,
    }

    gusset_dict = None
    if res.gusset is not None:
        g = res.gusset
        gusset_dict = {
            "gusset_type": g.gusset_type,
            "depth":       _clean(g.depth),
            "thickness":   _clean(g.thickness),
            "mass":        _clean(g.mass),
            "label":       g.label,
        }

    return {
        "plate_stress":      _clean(res.plate_stress),
        "plate_deflection":  _clean(res.plate_deflection),
        "plate_fos":         _clean(res.plate_fos),
        "bolt":              bolt_dict,
        "overall_fos":       _clean(res.overall_fos),
        "safe":              res.safe,
        "controlling":       res.controlling,
        "gusset":            gusset_dict,
        "plate_mass":        _clean(res.plate_mass),
        "total_mass":        _clean(res.total_mass),
    }


@app.post("/api/bracket/evaluate")
def bracket_evaluate(req: BracketEvaluateRequest):
    """Full bracket analysis: plate bending + bolt group + gusset."""
    try:
        mat = MATERIALS[req.material_key]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown material_key '{req.material_key}'. "
                   f"Valid keys: {list(MATERIALS.keys())}",
        )

    try:
        result = evaluate_bracket(
            P=req.P,
            e=req.e,
            width=req.width,
            thickness=req.thickness,
            mat=mat,
            fos_target=req.fos_target,
            bolt_count=req.bolt_count,
            bolt_diameter=req.bolt_diameter,
            bolt_spacing_v=req.bolt_spacing_v,
            bolt_sigma_allow=req.bolt_sigma_allow,
            deflection_limit=req.deflection_limit,
            gusset_type=req.gusset_type,
            gusset_depth=req.gusset_depth,
            gusset_thickness=req.gusset_thickness,
            edge_distance=req.edge_distance,
        )
    except (ValueError, ZeroDivisionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _json_response(_serialise_bracket_result(result))


# ===========================================================================
# POST — Bracket: compare all gusset types
# ===========================================================================

@app.post("/api/bracket/compare-gussets")
def bracket_compare_gussets(req: BracketCompareGussetsRequest):
    """Evaluate all gusset variants and return one result per gusset type."""
    try:
        mat = MATERIALS[req.material_key]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown material_key '{req.material_key}'.",
        )

    try:
        results = compare_gussets(
            P=req.P,
            e=req.e,
            width=req.width,
            thickness=req.thickness,
            mat=mat,
            fos_target=req.fos_target,
            bolt_count=req.bolt_count,
            bolt_diameter=req.bolt_diameter,
            bolt_spacing_v=req.bolt_spacing_v,
            bolt_sigma_allow=req.bolt_sigma_allow,
            deflection_limit=req.deflection_limit,
            gusset_depth=req.gusset_depth,
            gusset_thickness=req.gusset_thickness,
            edge_distance=req.edge_distance,
        )
    except (ValueError, ZeroDivisionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _json_response({
        "results": [_serialise_bracket_result(r) for r in results]
    })


# ===========================================================================
# POST — Stock: nearest buyable size
# ===========================================================================

@app.post("/api/stock/nearest-buyable")
def stock_nearest_buyable(req: StockNearestRequest):
    """
    Snap a theoretical design (described by material, section, and dims_mm)
    to the nearest stock size and return a comparison.

    The ``dims_mm`` field should contain at minimum ``d_mm`` (the primary
    outer dimension in mm).  For thin-walled sections also pass ``w_mm``
    (wall thickness in mm) or ``di_mm`` (inner diameter in mm) as appropriate.

    Internally we first build a minimal synthetic row that mirrors the
    DataFrame format used by nearest_buyable(), then call that function.
    """
    try:
        mat = MATERIALS[req.material_key]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown material_key '{req.material_key}'.",
        )

    # Build a synthetic dims string matching the optimizer format so that
    # stock._parse_dims can parse it back.
    sec = req.section_type
    dims = req.dims_mm
    d_mm = dims.get("d_mm", 30.0)

    if sec == "rectangle":
        dims_str = f"{d_mm:.0f}x{d_mm:.0f} mm"
    elif sec == "circle":
        dims_str = f"d={d_mm:.0f} mm"
    elif sec == "i_beam":
        tf_mm = dims.get("w_mm", d_mm / 10)
        dims_str = f"{d_mm:.0f}x{d_mm:.0f} tf={tf_mm:.0f} tw={tf_mm:.0f} mm"
    elif sec == "square_tube":
        w_mm = dims.get("w_mm", d_mm / 10)
        dims_str = f"{d_mm:.0f}x{d_mm:.0f} w={w_mm:.0f} mm"
    elif sec == "hollow_rectangle":
        w_mm = dims.get("w_mm", d_mm / 10)
        dims_str = f"{d_mm:.0f}x{d_mm:.0f} w={w_mm:.0f} mm"
    elif sec == "hollow_circle":
        di_mm = dims.get("di_mm", d_mm * 0.8)
        dims_str = f"d={d_mm:.0f} di={di_mm:.0f} mm"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown section_type '{sec}'.")

    # Build section properties for the theoretical design so we can populate
    # weight, cost, I, fos for the original dict.
    from modulus.optimizer import _section_config
    d = d_mm / 1000.0
    config = _section_config(sec, d, d_mm)
    if config is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid geometry for section_type='{sec}' at d_mm={d_mm}.",
        )
    sec_fn, sec_dims, _ = config
    try:
        props = sec_fn(*sec_dims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    M = max_moment(req.load, req.length, req.load_case)
    sigma = max_stress(M, props)
    delta = max_deflection(req.load, req.length, mat.E, props, req.load_case)
    fos_val = factor_of_safety(sigma, mat.sigma_y)
    weight = props.A * req.length * mat.rho
    cost = weight * mat.cost
    defl_ok = (req.deflection_limit is None) or (delta <= req.deflection_limit)

    theoretical = {
        "material":   mat.name,
        "section":    sec,
        "dims":       dims_str,
        "area":       props.A,
        "I":          props.I,
        "weight":     weight,
        "cost":       cost,
        "stress":     sigma,
        "deflection": delta,
        "fos":        fos_val,
        "safe":       (fos_val >= req.fos_target) and defl_ok,
    }

    try:
        comparison = nearest_buyable(
            theoretical=theoretical,
            load=req.load,
            length=req.length,
            load_case=req.load_case,
            fos_target=req.fos_target,
            deflection_limit=req.deflection_limit,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _json_response({
        "original":           _clean(comparison.original),
        "snapped":            _clean(comparison.snapped),
        "snapped_dims_mm":    _clean(comparison.snapped_dims_mm),
        "mass_penalty_pct":   _clean(comparison.mass_penalty_pct),
        "stiffness_change_pct": _clean(comparison.stiffness_change_pct),
        "fos_change":         _clean(comparison.fos_change),
        "summary":            comparison.summary,
    })


# ===========================================================================
# POST — Export: file download
# ===========================================================================

_EXPORT_MEDIA_TYPES = {
    "csv":  "text/csv",
    "json": "application/json",
    "text": "text/plain",
    "pdf":  "application/pdf",
}

_EXPORT_FILENAMES = {
    "csv":  "modulus_report.csv",
    "json": "modulus_report.json",
    "text": "modulus_report.txt",
    "pdf":  "modulus_report.pdf",
}


@app.post("/api/export")
def export_report(req: ExportRequest):
    """
    Run the beam sweep, generate a design review, and return the report as a
    file download in the requested format (csv | json | text | pdf).
    """
    fmt = req.format.lower()
    if fmt not in _EXPORT_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{fmt}'. Choose one of: csv, json, text, pdf.",
        )

    try:
        df = _run_sweep(req)
        winner = recommend(df, priority=req.priority)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        review = generate_review(
            winner=winner,
            df=df,
            priority=req.priority,
            load=req.load,
            length=req.length,
            load_case=req.load_case,
            fos_target=req.fos_target,
            deflection_limit=req.deflection_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Review generation failed: {exc}",
        )

    # rank_candidates is already imported at module level
    ranked_df = rank_candidates(df, priority=req.priority)

    problem = {
        "load":             req.load,
        "length":           req.length,
        "load_case":        req.load_case,
        "fos_target":       req.fos_target,
        "deflection_limit": req.deflection_limit,
    }

    try:
        report_bytes = export_report_bytes(
            df=ranked_df,
            review=review,
            problem=problem,
            priority=req.priority,
            fmt=fmt,
        )
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}")

    return Response(
        content=report_bytes,
        media_type=_EXPORT_MEDIA_TYPES[fmt],
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_EXPORT_FILENAMES[fmt]}"'
            )
        },
    )


# ===========================================================================
# Static SPA: serve the built React app for all non-/api routes.
# Mounted last so the API routes above win. html=True serves index.html at "/"
# and resolves the hashed /assets/* files, giving a single-service deployment.
# Guarded so the API still runs (tests, dev) when the frontend isn't built.
# ===========================================================================

if _os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="spa")


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

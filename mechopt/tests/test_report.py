"""Report export tests — CSV, JSON, text report generation."""

import json
import os
import tempfile

import pytest
import pandas as pd

from mechopt.optimizer import evaluate_candidates, recommend
from mechopt.decision import rank_candidates
from mechopt.design_review import generate_review
from mechopt.report import (
    export_csv,
    export_json,
    generate_text_report,
    export_report_bytes,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def analysis():
    """Run a standard analysis and return (df, review, problem, priority)."""
    load, length, load_case = 500.0, 1.0, "cantilever_end"
    fos_target = 2.0
    priority = "balanced"

    df = evaluate_candidates(
        load, length, load_case, fos_target,
        material_keys=["steel_a36", "aluminum_6061"],
        section_types=["rectangle", "circle"],
    )
    df = rank_candidates(df, priority)
    rec = recommend(df, priority)
    review = generate_review(
        winner=rec, df=df, priority=priority,
        load=load, length=length, load_case=load_case,
        fos_target=fos_target,
    )
    problem = {
        "load": load, "length": length, "load_case": load_case,
        "fos_target": fos_target, "deflection_limit": None,
    }
    return df, review, problem, priority


# ── CSV tests ───────────────────────────────────────────────────────────────

def test_csv_export_creates_file(analysis):
    df, review, problem, priority = analysis
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        result = export_csv(df, path)
        assert result == path
        assert os.path.exists(path)
        # Read back and verify
        loaded = pd.read_csv(path)
        assert len(loaded) == len(df)
        assert "safety_case" not in loaded.columns
        assert "material" in loaded.columns
        assert "fos" in loaded.columns
    finally:
        os.unlink(path)


def test_csv_excludes_safety_case(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "csv")
    text = data.decode("utf-8")
    assert "safety_case" not in text
    assert "material" in text


# ── JSON tests ──────────────────────────────────────────────────────────────

def test_json_export_creates_file(analysis):
    df, review, problem, priority = analysis
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        result = export_json(df, review, path)
        assert result == path
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        assert "generated" in payload
        assert "candidates" in payload
        assert "review" in payload
        assert len(payload["candidates"]) == len(df)
    finally:
        os.unlink(path)


def test_json_review_has_expected_keys(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "json")
    payload = json.loads(data.decode("utf-8"))
    r = payload["review"]
    assert "recommended" in r
    assert "why_it_won" in r
    assert "controlling_constraint" in r
    assert "sensitivities" in r
    assert "unmodeled_risks" in r


def test_json_candidates_have_no_safety_case(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "json")
    payload = json.loads(data.decode("utf-8"))
    for cand in payload["candidates"]:
        assert "safety_case" not in cand


# ── Text report tests ──────────────────────────────────────────────────────

def test_text_report_contains_sections(analysis):
    df, review, problem, priority = analysis
    text = generate_text_report(df, review, problem, priority)
    assert "PROBLEM DEFINITION" in text
    assert "CANDIDATE SUMMARY" in text
    assert "TOP CANDIDATES" in text
    assert "RECOMMENDED DESIGN" in text
    assert "FAILURE-MODE TABLE" in text
    assert "LIMITATIONS" in text
    assert "MechOpt" in text


def test_text_report_contains_problem_values(analysis):
    df, review, problem, priority = analysis
    text = generate_text_report(df, review, problem, priority)
    assert "500" in text       # load
    assert "cantilever" in text


def test_text_report_contains_review_info(analysis):
    df, review, problem, priority = analysis
    text = generate_text_report(df, review, problem, priority)
    assert review.controlling_constraint in text
    assert review.recommended in text


# ── export_report_bytes tests ───────────────────────────────────────────────

def test_export_bytes_csv_returns_bytes(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "csv")
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_export_bytes_json_returns_bytes(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "json")
    assert isinstance(data, bytes)
    # Verify it's valid JSON
    json.loads(data.decode("utf-8"))


def test_export_bytes_text_returns_bytes(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "text")
    assert isinstance(data, bytes)
    assert b"MechOpt" in data


def test_export_bytes_pdf_returns_bytes(analysis):
    df, review, problem, priority = analysis
    data = export_report_bytes(df, review, problem, priority, "pdf")
    assert isinstance(data, bytes)
    assert len(data) > 1000
    assert data[:5] == b"%PDF-"


def test_export_bytes_invalid_format(analysis):
    df, review, problem, priority = analysis
    with pytest.raises(ValueError):
        export_report_bytes(df, review, problem, priority, "xlsx")

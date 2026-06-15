"""Streamlit UI for MechOpt — Mechanical Design Screening Dashboard.

Run locally:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from mechopt.beam import max_deflection, max_moment, max_stress, factor_of_safety
from mechopt.bracket import evaluate_bracket
from mechopt.components.section_editor import section_editor
from mechopt.materials import MATERIALS
from mechopt.optimizer import evaluate_candidates, recommend
from mechopt.sections import (
    circle, hollow_circle, hollow_rectangle, i_beam, rectangle, square_tube,
)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MechOpt", page_icon="wrench", layout="wide")

# ─── Custom CSS to match index.html design ────────────────────────────────────
st.markdown("""
<style>
  :root {
    --bg: #0e1117; --surface: #1a1d24; --card: #262730;
    --border: #3d4050; --text: #fafafa; --muted: #a0a4b0;
    --accent: #4a9eff; --green: #28a745; --red: #dc3545;
    --yellow: #ffc107; --radius: 8px;
  }

  /* Hide default Streamlit header/footer */
  header[data-testid="stHeader"] { background: var(--bg) !important; }
  .stApp { background: var(--bg); }

  /* Tab styling */
  button[data-baseweb="tab"] {
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    color: var(--muted) !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 20px !important;
  }
  button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
  }

  /* Metric cards */
  div[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
  }
  div[data-testid="stMetric"] label {
    font-size: 0.75rem !important;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
    font-weight: 700 !important;
  }
  div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
  }

  /* Expander styling */
  details[data-testid="stExpander"] {
    background: var(--card);
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
  }
  details[data-testid="stExpander"] summary {
    font-weight: 500;
  }
  details[data-testid="stExpander"] summary:hover {
    border-color: var(--accent) !important;
  }

  /* Section headers */
  h2, h3 {
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
  }
  h3 { font-size: 1rem !important; }

  /* Dividers */
  hr { border-color: var(--border) !important; }

  /* Dataframe */
  div[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  /* Custom badge */
  .mechopt-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.85rem;
  }
  .badge-safe {
    background: #1a3d1a;
    color: var(--green);
    border: 1px solid var(--green);
  }
  .badge-unsafe {
    background: #3d1a1a;
    color: var(--red);
    border: 1px solid var(--red);
  }

  /* Recommendation header */
  .rec-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding: 8px 0;
  }
  .rec-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text);
  }

  /* Alert boxes */
  .mechopt-alert {
    padding: 12px 16px;
    border-radius: var(--radius);
    margin-bottom: 16px;
    border-left: 4px solid;
    font-size: 0.9rem;
    line-height: 1.5;
  }
  .alert-info { background: #1e3a5f; border-color: var(--accent); color: var(--text); }
  .alert-success { background: #1a3d1a; border-color: var(--green); color: var(--text); }
  .alert-warning { background: #3d2e00; border-color: var(--yellow); color: var(--text); }
  .alert-danger { background: #3d1a1a; border-color: var(--red); color: var(--text); }

  /* Panel */
  .mechopt-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
  }

  /* Assumptions list */
  .assumptions-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .assumptions-list li {
    padding: 4px 0 4px 16px;
    position: relative;
    font-size: 0.9rem;
    color: var(--text);
  }
  .assumptions-list li::before {
    content: "·";
    position: absolute;
    left: 4px;
    color: var(--accent);
    font-weight: bold;
  }

  /* Subtitle */
  .mechopt-subtitle {
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 20px;
  }

  /* Custom table styling */
  .mechopt-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .mechopt-table th {
    background: var(--card);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    color: var(--muted);
    border-bottom: 2px solid var(--border);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .mechopt-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
  }
  .mechopt-table tr:hover { background: var(--card); }
  .mechopt-table .text-right { text-align: right; }
  .mechopt-table .safe-row td { border-left: 3px solid var(--green); }
  .mechopt-table .unsafe-row td:first-child { border-left: 3px solid var(--red); }
  .mini-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 0.75rem;
  }
</style>
""", unsafe_allow_html=True)


# ─── Title ────────────────────────────────────────────────────────────────────
st.markdown("# &#9881; MechOpt")
st.markdown('<p class="mechopt-subtitle">Mechanical Design Screening Dashboard &mdash; First-pass static analysis for beams and brackets</p>', unsafe_allow_html=True)

tab_beam, tab_bracket, tab_compare, tab_assumptions = st.tabs([
    "Beam Optimizer", "Bracket Analysis", "Compare Designs",
    "Assumptions & Limitations",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BEAM OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_beam:

    # ── Inputs ────────────────────────────────────────────────────────────────
    inp_left, inp_right = st.columns([3, 1])

    with inp_left:
        st.subheader("Loading")
        lc1, lc2, lc3, lc4 = st.columns(4)
        with lc1:
            load = st.number_input("Load P (N)", min_value=1.0, value=500.0,
                                   step=50.0, key="beam_load")
        with lc2:
            length = st.number_input("Span L (m)", min_value=0.01, value=1.0,
                                     step=0.1, key="beam_length")
        with lc3:
            load_case = st.selectbox("Load Case",
                                     ["cantilever_end", "simply_center"],
                                     format_func=lambda x: x.replace("_", " ").title(),
                                     key="beam_lc")
        with lc4:
            fos_target = st.number_input("Target FoS", min_value=1.0,
                                         value=2.0, step=0.5, key="beam_fos")

    with inp_right:
        st.subheader("Objective")
        priority = st.selectbox("Priority",
                                ["balanced", "lightest", "cheapest", "safest"],
                                format_func=str.title,
                                key="beam_prio")
        defl_limit_mm = st.number_input(
            "Max Deflection (mm)", min_value=0.0, value=0.0, step=0.5,
            help="0 = no deflection limit", key="beam_defl")
        deflection_limit = defl_limit_mm / 1000.0 if defl_limit_mm > 0 else None

    with st.expander("Material & Section Filters", expanded=False):
        fc1, fc2 = st.columns(2)
        mat_options = {k: v.name for k, v in MATERIALS.items()}
        with fc1:
            selected_mats = st.multiselect(
                "Materials", options=list(mat_options.keys()),
                default=list(mat_options.keys()),
                format_func=lambda k: mat_options[k], key="beam_mats")
        with fc2:
            all_secs = ["rectangle", "circle", "i_beam", "square_tube",
                        "hollow_rectangle", "hollow_circle"]
            selected_secs = st.multiselect(
                "Section Types", options=all_secs,
                default=["rectangle", "circle"],
                format_func=lambda s: s.replace("_", " ").title(),
                key="beam_secs")

    if not selected_mats:
        selected_mats = list(MATERIALS.keys())
    if not selected_secs:
        selected_secs = ["rectangle", "circle"]

    # ── Evaluate ──────────────────────────────────────────────────────────────
    try:
        df = evaluate_candidates(
            float(load), float(length), str(load_case), float(fos_target),
            material_keys=list(selected_mats),
            section_types=list(selected_secs),
            deflection_limit=float(deflection_limit) if deflection_limit is not None else None,
        )
    except Exception as e:
        st.error(f"Error evaluating candidates: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

    safe = df[df["safe"]]
    total_count = len(df)
    safe_count = len(safe)

    # ── Recommendation card ───────────────────────────────────────────────────
    st.divider()

    if safe.empty:
        st.markdown(
            '<div class="mechopt-alert alert-danger">'
            f'No safe design found among {total_count} candidates. '
            'Try reducing the load, lowering the FoS target, or relaxing the deflection limit.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        rec = recommend(df, priority)

        # Controlling constraint
        fos_ratio = fos_target / rec["fos"] if rec["fos"] > 0 else 1.0
        if deflection_limit is not None and deflection_limit > 0:
            defl_ratio = rec["deflection"] / deflection_limit
        else:
            defl_ratio = 0.0

        if deflection_limit is not None and defl_ratio > fos_ratio:
            controlling = "Deflection"
        elif fos_ratio > 0.5:
            controlling = "Stress / Yielding"
        else:
            controlling = {"lightest": "Weight", "cheapest": "Cost"}.get(
                priority, "Stress / Yielding")

        # Status header with badge
        badge_cls = "badge-safe" if rec["safe"] else "badge-unsafe"
        badge_text = "SAFE" if rec["safe"] else "UNSAFE"
        st.markdown(
            f'<div class="rec-header">'
            f'<span class="rec-title">Recommended: {rec["material"]} &mdash; {rec["section"]} ({rec["dims"]})</span>'
            f'<span class="mechopt-badge {badge_cls}">{badge_text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Metrics
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        delta_fos = rec["fos"] - fos_target
        m1.metric("FoS", f"{rec['fos']:.2f}", delta=f"{delta_fos:+.2f} vs target")
        m2.metric("Stress", f"{rec['stress'] / 1e6:.1f} MPa")
        m3.metric("Deflection", f"{rec['deflection'] * 1e3:.2f} mm")
        m4.metric("Weight", f"{rec['weight']:.4f} kg")
        m5.metric("Cost", f"${rec['cost']:.2f}")
        m6.metric("Controls", controlling)

        # Explanation
        defl_str = f"{rec['deflection'] * 1e3:.2f} mm"
        if deflection_limit is not None:
            defl_str += f" (limit: {defl_limit_mm:.1f} mm)"
        st.markdown(
            f'<div class="mechopt-alert alert-info">'
            f'Selected as the <strong>{priority}</strong> safe option from '
            f'<strong>{safe_count}</strong> safe / <strong>{total_count}</strong> total candidates. '
            f'Stress FoS = <strong>{rec["fos"]:.2f}</strong> (target {fos_target:.1f}). '
            f'Deflection = <strong>{defl_str}</strong>.'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Interactive Section Editor ───────────────────────────────────────────
    if not safe.empty:
        st.divider()
        st.subheader("Interactive Section Editor")
        st.markdown(
            '<div class="mechopt-alert alert-info">'
            'Edit dimensions below or drag the blue handles on the drawing. '
            'Python recomputes stress, deflection, and FoS on every change.'
            '</div>',
            unsafe_allow_html=True,
        )

        # Determine the section type and dims from the recommendation
        _sec_name = rec["section"]
        _sec_dims_str = rec["dims"]  # e.g. "30x30 mm", "d=30 mm"
        _sec_mat_key = [k for k, v in MATERIALS.items() if v.name == rec["material"]][0]
        _sec_mat = MATERIALS[_sec_mat_key]

        # Parse dims from the recommendation row to build initial dims dict
        _editor_dims = {}
        _d_mm = float(rec.get("dims", "30").split("=")[-1].split("x")[0].split()[0]) if rec["dims"] else 30.0
        if _sec_name == "rectangle":
            # dims like "30x30 mm"
            parts = rec["dims"].replace(" mm", "").split("x")
            _editor_dims = {"b": float(parts[0]) / 1000, "h": float(parts[1]) / 1000}
        elif _sec_name == "circle":
            # dims like "d=30 mm"
            val = float(rec["dims"].replace("d=", "").replace(" mm", ""))
            _editor_dims = {"d": val / 1000}
        elif _sec_name == "i_beam":
            # dims like "30x30 tf=3.0/tw=3.0 mm"
            parts = rec["dims"].replace(" mm", "").split()
            outer = parts[0].split("x")
            tf_val = float(parts[1].split("=")[1].split("/")[0])
            tw_val = float(parts[1].split("=")[1].split("/")[1] if "/" in parts[1] else parts[2].split("=")[1])
            _editor_dims = {"b": float(outer[0]) / 1000, "h": float(outer[1]) / 1000,
                            "tf": tf_val / 1000, "tw": tw_val / 1000}
        elif _sec_name == "square_tube":
            # dims like "30x30 w=3.0 mm"
            parts = rec["dims"].replace(" mm", "").split()
            a_val = float(parts[0].split("x")[0])
            w_val = float(parts[1].split("=")[1])
            _editor_dims = {"a": a_val / 1000, "w": w_val / 1000}
        elif _sec_name == "hollow_rectangle":
            # dims like "30x30 w=3.0 mm"
            parts = rec["dims"].replace(" mm", "").split()
            outer = parts[0].split("x")
            w_val = float(parts[1].split("=")[1])
            _editor_dims = {"b": float(outer[0]) / 1000, "h": float(outer[1]) / 1000,
                            "w": w_val / 1000}
        elif _sec_name == "hollow_circle":
            # dims like "d=30 di=22.0 mm" or "d=30/di=22 mm"
            text = rec["dims"].replace(" mm", "")
            d_val = float(text.split("d=")[1].split()[0].split("/")[0])
            di_val = float(text.split("di=")[1].split()[0])
            _editor_dims = {"d": d_val / 1000, "di": di_val / 1000}
        else:
            _editor_dims = {"b": 0.03, "h": 0.03}

        # Check if user has edited dims via the component
        _editor_results = {
            "stress": rec["stress"],
            "deflection": rec["deflection"],
            "fos": rec["fos"],
            "safe": bool(rec["safe"]),
        }

        # Use session state to persist user-edited dims across reruns
        _state_key = "editor_dims"
        if _state_key not in st.session_state:
            st.session_state[_state_key] = None

        _active_dims = st.session_state[_state_key] if st.session_state[_state_key] else _editor_dims

        # Recompute with active dims
        try:
            if _sec_name == "rectangle":
                _props = rectangle(_active_dims["b"], _active_dims["h"])
            elif _sec_name == "circle":
                _props = circle(_active_dims["d"])
            elif _sec_name == "i_beam":
                _props = i_beam(_active_dims["b"], _active_dims["h"],
                                _active_dims["tf"], _active_dims["tw"])
            elif _sec_name == "square_tube":
                _props = square_tube(_active_dims["a"], _active_dims["w"])
            elif _sec_name == "hollow_rectangle":
                _props = hollow_rectangle(_active_dims["b"], _active_dims["h"],
                                          _active_dims["w"])
            elif _sec_name == "hollow_circle":
                _props = hollow_circle(_active_dims["d"], _active_dims["di"])
            else:
                _props = rectangle(_active_dims.get("b", 0.03), _active_dims.get("h", 0.03))

            _M = max_moment(float(load), float(length), str(load_case))
            _sigma = max_stress(_M, _props)
            _delta = max_deflection(float(load), float(length), _sec_mat.E, _props,
                                    str(load_case))
            _fos = factor_of_safety(_sigma, _sec_mat.sigma_y)
            _is_safe = _fos >= float(fos_target)
            if deflection_limit is not None and _delta > deflection_limit:
                _is_safe = False

            _editor_results = {
                "stress": _sigma,
                "deflection": _delta,
                "fos": _fos,
                "safe": _is_safe,
            }
        except (ValueError, ZeroDivisionError):
            pass  # keep previous results on invalid geometry

        user_dims = section_editor(
            section=_sec_name,
            dims=_active_dims,
            results=_editor_results,
            key="sec_editor",
        )

        if user_dims is not None:
            st.session_state[_state_key] = user_dims
            st.rerun()

    # ── Candidate table (custom HTML table matching index.html) ───────────────
    st.divider()
    with st.expander(f"All Candidates ({safe_count} safe / {total_count} total)",
                     expanded=False):
        table_html = (
            '<div style="overflow-x:auto;">'
            '<table class="mechopt-table"><thead><tr>'
            '<th>Material</th><th>Section</th><th>Dims</th>'
            '<th class="text-right">FoS</th><th class="text-right">Stress (MPa)</th>'
            '<th class="text-right">Defl (mm)</th><th class="text-right">Weight (kg)</th>'
            '<th class="text-right">Cost ($)</th><th>Safe</th>'
            '</tr></thead><tbody>'
        )
        for _, row in df.iterrows():
            row_cls = "safe-row" if row["safe"] else "unsafe-row"
            badge_cls = "badge-safe" if row["safe"] else "badge-unsafe"
            safe_text = "Yes" if row["safe"] else "No"
            table_html += (
                f'<tr class="{row_cls}">'
                f'<td>{row["material"]}</td>'
                f'<td>{row["section"]}</td>'
                f'<td>{row["dims"]}</td>'
                f'<td class="text-right">{row["fos"]:.2f}</td>'
                f'<td class="text-right">{row["stress"] / 1e6:.1f}</td>'
                f'<td class="text-right">{row["deflection"] * 1e3:.2f}</td>'
                f'<td class="text-right">{row["weight"]:.4f}</td>'
                f'<td class="text-right">{row["cost"]:.2f}</td>'
                f'<td><span class="mini-badge {badge_cls}">{safe_text}</span></td>'
                f'</tr>'
            )
        table_html += '</tbody></table></div>'
        st.markdown(table_html, unsafe_allow_html=True)

    # ── Tradeoff plots ────────────────────────────────────────────────────────
    with st.expander("Tradeoff Plots", expanded=True):
        pc1, pc2 = st.columns(2)
        with pc1:
            st.caption("Weight vs FoS")
            st.scatter_chart(df, x="weight", y="fos", color="material",
                             x_label="Weight (kg)", y_label="Factor of Safety")
        with pc2:
            st.caption("Cost vs FoS")
            st.scatter_chart(df, x="cost", y="fos", color="material",
                             x_label="Cost ($)", y_label="Factor of Safety")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BRACKET ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_bracket:
    st.markdown(
        '<p class="mechopt-subtitle">Simplified cantilever plate with bolt group &mdash; see Assumptions tab</p>',
        unsafe_allow_html=True,
    )

    # ── Inputs in two panels ─────────────────────────────────────────────────
    col_plate, col_bolts = st.columns(2)

    with col_plate:
        st.markdown('<div class="mechopt-panel">', unsafe_allow_html=True)
        st.subheader("Plate / Arm")
        pc1, pc2 = st.columns(2)
        with pc1:
            br_load = st.number_input("Load P (N)", min_value=1.0, value=500.0,
                                      step=50.0, key="br_load")
            br_offset = st.number_input("Load Offset e (mm)", min_value=1.0,
                                        value=150.0, step=10.0, key="br_offset") / 1000.0
            mat_options_br = {k: v.name for k, v in MATERIALS.items()}
            br_mat_key = st.selectbox("Material",
                                      options=list(mat_options_br.keys()),
                                      format_func=lambda k: mat_options_br[k],
                                      key="br_mat")
        with pc2:
            br_width = st.number_input("Width (mm)", min_value=5.0,
                                       value=80.0, step=5.0, key="br_w") / 1000.0
            br_thick = st.number_input("Thickness (mm)", min_value=1.0,
                                       value=10.0, step=1.0, key="br_t") / 1000.0
            br_fos = st.number_input("Target FoS", min_value=1.0, value=2.0,
                                     step=0.5, key="br_fos")
            br_defl_mm = st.number_input("Max Deflection (mm), 0 = none",
                                         min_value=0.0, value=0.0, step=0.5,
                                         key="br_defl")
            br_defl_limit = br_defl_mm / 1000.0 if br_defl_mm > 0 else None
        st.markdown('</div>', unsafe_allow_html=True)

    with col_bolts:
        st.markdown('<div class="mechopt-panel">', unsafe_allow_html=True)
        st.subheader("Bolt Group")
        bc1, bc2 = st.columns(2)
        with bc1:
            bolt_count = st.number_input("Bolt Count", min_value=1,
                                         value=4, step=1, key="br_bn")
            bolt_dia = st.number_input("Bolt Diameter (mm)", min_value=2.0,
                                       value=10.0, step=1.0, key="br_bd") / 1000.0
        with bc2:
            bolt_spacing = st.number_input("Vertical Spacing (mm)",
                                           min_value=5.0, value=40.0, step=5.0,
                                           key="br_bs") / 1000.0
            bolt_allow = st.number_input("Bolt Allowable Stress (MPa)",
                                         min_value=50.0, value=640.0, step=50.0,
                                         key="br_ba") * 1e6
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    mat = MATERIALS[br_mat_key]
    result = evaluate_bracket(
        P=br_load, e=br_offset, width=br_width, thickness=br_thick,
        mat=mat, fos_target=br_fos, bolt_count=bolt_count,
        bolt_diameter=bolt_dia, bolt_spacing_v=bolt_spacing,
        bolt_sigma_allow=bolt_allow, deflection_limit=br_defl_limit,
    )

    # ── Results ───────────────────────────────────────────────────────────────
    st.divider()

    ctrl_label = result.controlling.replace("_", " ").title()
    badge_cls = "badge-safe" if result.safe else "badge-unsafe"
    badge_text = "SAFE" if result.safe else "UNSAFE"

    st.markdown(
        f'<div class="rec-header">'
        f'<span class="rec-title">Result &mdash; Controlled by {ctrl_label}</span>'
        f'<span class="mechopt-badge {badge_cls}">{badge_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Overall metrics
    ov1, ov2, ov3 = st.columns(3)
    delta_fos_br = result.overall_fos - br_fos
    ov1.metric("Overall FoS", f"{result.overall_fos:.2f}",
               delta=f"{delta_fos_br:+.2f} vs target")
    ov2.metric("Plate Deflection", f"{result.plate_deflection * 1e3:.3f} mm")
    ov3.metric("Moment", f"{br_load * br_offset:.1f} N-m")

    # Plate vs Bolt side-by-side in panels
    res_plate, res_bolt = st.columns(2)

    with res_plate:
        st.markdown('<div class="mechopt-panel">', unsafe_allow_html=True)
        st.markdown("### Plate")
        pp1, pp2, pp3 = st.columns(3)
        pp1.metric("Stress", f"{result.plate_stress / 1e6:.1f} MPa")
        pp2.metric("FoS", f"{result.plate_fos:.2f}")
        pp3.metric("Deflection", f"{result.plate_deflection * 1e3:.3f} mm")
        st.markdown('</div>', unsafe_allow_html=True)

    with res_bolt:
        st.markdown('<div class="mechopt-panel">', unsafe_allow_html=True)
        st.markdown("### Bolt Group")
        bb1, bb2, bb3, bb4 = st.columns(4)
        bb1.metric("Shear/Bolt", f"{result.bolt.shear_per_bolt:.1f} N")
        bb2.metric("Max Tension", f"{result.bolt.max_tension:.1f} N")
        bb3.metric("Bolt FoS", f"{result.bolt.bolt_fos:.2f}")
        bb4.metric("Utilization", f"{result.bolt.combined_utilization:.0%}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Engineering interpretation
    if result.controlling == "plate_bending":
        advice = (
            "<strong>Plate bending</strong> controls this design. Bending stiffness scales "
            "with thickness cubed (I ~ t&sup3;), so increasing plate thickness is "
            "the most effective change. Switching to a higher-strength material will also help."
        )
    elif result.controlling == "bolt":
        advice = (
            "The <strong>bolt group</strong> controls this design. Consider larger bolt "
            "diameter, more bolts, or greater vertical spacing. Increasing plate thickness "
            "will not help bolt stresses."
        )
    elif result.controlling == "deflection":
        advice = (
            "<strong>Deflection</strong> controls this design. Consider thicker plate, "
            "stiffer material (higher E), or shorter load offset."
        )
    else:
        advice = "Design is within all limits."

    alert_cls = "alert-success" if result.safe else "alert-warning"
    st.markdown(
        f'<div class="mechopt-alert {alert_cls}">{advice}</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE DESIGNS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:

    # ── Winners summary ───────────────────────────────────────────────────────
    st.subheader("Beam Winners")
    safe_beams = df[df["safe"]]
    if safe_beams.empty:
        st.markdown(
            '<div class="mechopt-alert alert-warning">'
            'No safe beam designs. Adjust parameters in the Beam Optimizer tab.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        winners = {}
        for prio in ["lightest", "cheapest", "safest", "balanced"]:
            try:
                w = recommend(df, prio)
                winners[prio.title()] = {
                    "Material": w["material"],
                    "Section": f'{w["section"]} ({w["dims"]})',
                    "FoS": f'{w["fos"]:.2f}',
                    "Stress (MPa)": f'{w["stress"] / 1e6:.1f}',
                    "Defl (mm)": f'{w["deflection"] * 1e3:.2f}',
                    "Weight (kg)": f'{w["weight"]:.4f}',
                    "Cost ($)": f'{w["cost"]:.2f}',
                }
            except ValueError:
                pass

        if winners:
            winners_df = pd.DataFrame(winners).T
            winners_df.index.name = "Priority"
            st.dataframe(winners_df, width="stretch")

    # ── Top 5 tables (custom HTML) ───────────────────────────────────────────
    st.divider()
    st.subheader("Top 5 Safe Beams")

    if not safe_beams.empty:
        safe_fmt = safe_beams.copy()
        safe_fmt["Stress_MPa"] = safe_fmt["stress"] / 1e6
        safe_fmt["Defl_mm"] = safe_fmt["deflection"] * 1e3

        def mini_table_html(title, rows_df):
            html = f'<h3 style="margin-bottom:8px;">{title}</h3>'
            html += '<div style="overflow-x:auto;"><table class="mechopt-table"><thead><tr>'
            html += '<th>Material</th><th>Section</th><th>Dims</th>'
            html += '<th class="text-right">FoS</th><th class="text-right">Weight</th>'
            html += '<th class="text-right">Cost</th></tr></thead><tbody>'
            for _, r in rows_df.iterrows():
                html += (
                    f'<tr><td>{r["material"]}</td><td>{r["section"]}</td>'
                    f'<td>{r["dims"]}</td><td class="text-right">{r["fos"]:.2f}</td>'
                    f'<td class="text-right">{r["weight"]:.4f}</td>'
                    f'<td class="text-right">${r["cost"]:.2f}</td></tr>'
                )
            html += '</tbody></table></div>'
            return html

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.markdown(
                mini_table_html("Lightest", safe_fmt.nsmallest(5, "weight")),
                unsafe_allow_html=True,
            )
        with tc2:
            st.markdown(
                mini_table_html("Cheapest", safe_fmt.nsmallest(5, "cost")),
                unsafe_allow_html=True,
            )
        with tc3:
            st.markdown(
                mini_table_html("Safest", safe_fmt.nlargest(5, "fos")),
                unsafe_allow_html=True,
            )

    # ── Bracket summary ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Bracket Summary")

    if "result" not in dir():
        st.markdown(
            '<div class="mechopt-alert alert-info">'
            'Configure the Bracket Analysis tab to see results here.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        bs1, bs2, bs3, bs4, bs5 = st.columns(5)
        bs1.metric("Overall FoS", f"{result.overall_fos:.2f}")
        bs2.metric("Plate Stress", f"{result.plate_stress / 1e6:.1f} MPa")
        bs3.metric("Bolt FoS", f"{result.bolt.bolt_fos:.2f}")
        bs4.metric("Controls", result.controlling.replace("_", " ").title())
        badge_cls = "badge-safe" if result.safe else "badge-unsafe"
        badge_text = "SAFE" if result.safe else "UNSAFE"
        bs5.markdown(
            f'<div style="margin-top:8px;"><span class="mechopt-badge {badge_cls}">{badge_text}</span></div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ASSUMPTIONS & LIMITATIONS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_assumptions:

    st.markdown(
        '<div class="mechopt-alert alert-info">'
        'MechOpt is a <strong>first-pass screening tool</strong>. It is not a substitute '
        'for formal engineering analysis, detailed FEA, or professional review.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
<h2 style="text-transform:uppercase;letter-spacing:0.5px;">What IS Modeled</h2>
<ul class="assumptions-list">
  <li>Linear-elastic material behaviour (Hooke's law)</li>
  <li>Static point loads only</li>
  <li>Small-deflection Euler&ndash;Bernoulli beam theory</li>
  <li>Prismatic (constant cross-section) beams</li>
  <li>Yielding-based factor of safety</li>
  <li>Simplified cantilever plate model for brackets</li>
  <li>Linear elastic bolt group load distribution</li>
  <li>Direct shear equally distributed among bolts</li>
  <li>Moment-induced bolt tension from centroid distance</li>
</ul>
<h2 style="margin-top:20px;text-transform:uppercase;letter-spacing:0.5px;">Material Data</h2>
<ul class="assumptions-list">
  <li>Nominal room-temperature properties for typical grades</li>
  <li>Cost figures are rough order-of-magnitude</li>
  <li>Treat cost comparisons as <strong>relative</strong>, not absolute</li>
</ul>
""", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
<h2 style="text-transform:uppercase;letter-spacing:0.5px;">What is NOT Modeled</h2>
<h3>Beam</h3>
<ul class="assumptions-list">
  <li>Buckling (lateral-torsional or local)</li>
  <li>Stress concentrations (holes, notches, fillets)</li>
  <li>Fatigue or cyclic loading</li>
  <li>Shear deflection</li>
  <li>Dynamic or impact loads</li>
  <li>Weld or joint effects</li>
  <li>Thermal effects</li>
  <li>Combined loading (axial + bending + torsion)</li>
</ul>
<h3 style="margin-top:12px;">Bracket</h3>
<ul class="assumptions-list">
  <li>Weld design</li>
  <li>Stress concentrations at bolt holes</li>
  <li>Bearing, tear-out, or block shear</li>
  <li>Prying action</li>
  <li>Plate buckling</li>
  <li>Bolt preload / thread engagement</li>
  <li>FEA-level stress distribution</li>
</ul>
<h3 style="margin-top:12px;">General</h3>
<ul class="assumptions-list">
  <li>Corrosion / environmental degradation</li>
  <li>Non-linear material behaviour</li>
  <li>Large-deflection effects</li>
</ul>
""", unsafe_allow_html=True)

    st.markdown(
        '<div class="mechopt-alert alert-warning" style="margin-top:24px;">'
        '<strong>Warning:</strong> Do not use this tool as the sole basis for manufacturing or '
        'safety-critical design decisions. All results should be verified '
        'by a qualified engineer before use in any real application.'
        '</div>',
        unsafe_allow_html=True,
    )

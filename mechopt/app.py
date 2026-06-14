"""Streamlit UI for MechOpt — Mechanical Design Screening Dashboard.

Run locally:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from mechopt.bracket import evaluate_bracket
from mechopt.materials import MATERIALS
from mechopt.optimizer import evaluate_candidates, recommend

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MechOpt", page_icon="wrench", layout="wide")


st.title("MechOpt")
st.caption("Mechanical Design Screening Dashboard  --  First-pass static analysis for beams and brackets")

tab_beam, tab_bracket, tab_compare, tab_assumptions = st.tabs([
    "Beam Optimizer", "Bracket Analysis", "Compare Designs",
    "Assumptions & Limitations",
])



# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BEAM OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_beam:

    # ── Inputs ────────────────────────────────────────────────────────────────
    inp_left, inp_right = st.columns([2, 1])

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
        st.error(
            f"No safe design found among {total_count} candidates. "
            "Try reducing the load, lowering the FoS target, or relaxing the deflection limit."
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

        # Status header
        header_col, badge_col = st.columns([4, 1])
        with header_col:
            st.subheader(f"Recommended: {rec['material']}  --  {rec['section']} ({rec['dims']})")
        with badge_col:
            if rec["safe"]:
                st.success("SAFE")
            else:
                st.error("UNSAFE")

        # Metrics
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("FoS", f"{rec['fos']:.2f}", delta=f"{rec['fos'] - fos_target:+.2f} vs target")
        m2.metric("Stress", f"{rec['stress'] / 1e6:.1f} MPa")
        m3.metric("Deflection", f"{rec['deflection'] * 1e3:.2f} mm")
        m4.metric("Weight", f"{rec['weight']:.4f} kg")
        m5.metric("Cost", f"${rec['cost']:.2f}")
        m6.metric("Controls", controlling)

        # Explanation
        defl_str = f"{rec['deflection'] * 1e3:.2f} mm"
        if deflection_limit is not None:
            defl_str += f" (limit: {defl_limit_mm:.1f} mm)"
        st.info(
            f"Selected as the **{priority}** safe option from "
            f"**{safe_count}** safe / **{total_count}** total candidates. "
            f"Stress FoS = **{rec['fos']:.2f}** (target {fos_target:.1f}). "
            f"Deflection = **{defl_str}**. "
            f"Controlling constraint: **{controlling}**."
        )

    # ── Candidate table ───────────────────────────────────────────────────────
    st.divider()
    with st.expander(f"All Candidates ({safe_count} safe / {total_count} total)",
                     expanded=False):
        fmt_df = df.copy()
        fmt_df["Stress (MPa)"] = fmt_df["stress"] / 1e6
        fmt_df["Defl (mm)"] = fmt_df["deflection"] * 1e3
        fmt_df["FoS"] = fmt_df["fos"]
        fmt_df["Weight (kg)"] = fmt_df["weight"]
        fmt_df["Cost ($)"] = fmt_df["cost"]
        show_cols = ["material", "section", "dims", "FoS", "Stress (MPa)",
                     "Defl (mm)", "Weight (kg)", "Cost ($)", "safe"]
        st.dataframe(
            fmt_df[show_cols].style.map(
                lambda v: "background-color: #d4edda" if v is True
                else ("background-color: #f8d7da" if v is False else ""),
                subset=["safe"]
            ),
            width="stretch", hide_index=True,
        )

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
    st.caption("Simplified cantilever plate with bolt group  --  see Assumptions tab")

    # ── Inputs in two sections ────────────────────────────────────────────────
    col_plate, col_bolts = st.columns(2)

    with col_plate:
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

    with col_bolts:
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

    # Status header
    hdr_col, badge_col2 = st.columns([4, 1])
    with hdr_col:
        ctrl_label = result.controlling.replace("_", " ").title()
        st.subheader(f"Result  --  Controlled by {ctrl_label}")
    with badge_col2:
        if result.safe:
            st.success("SAFE")
        else:
            st.error("UNSAFE")

    # Overall metrics
    ov1, ov2, ov3 = st.columns(3)
    ov1.metric("Overall FoS", f"{result.overall_fos:.2f}",
               delta=f"{result.overall_fos - br_fos:+.2f} vs target")
    ov2.metric("Plate Deflection", f"{result.plate_deflection * 1e3:.3f} mm")
    ov3.metric("Moment", f"{br_load * br_offset:.1f} N-m")

    # Plate vs Bolt side-by-side
    res_plate, res_bolt = st.columns(2)

    with res_plate:
        st.markdown("**Plate**")
        pp1, pp2, pp3 = st.columns(3)
        pp1.metric("Stress", f"{result.plate_stress / 1e6:.1f} MPa")
        pp2.metric("FoS", f"{result.plate_fos:.2f}")
        pp3.metric("Deflection", f"{result.plate_deflection * 1e3:.3f} mm")

    with res_bolt:
        st.markdown("**Bolt Group**")
        bb1, bb2, bb3, bb4 = st.columns(4)
        bb1.metric("Shear/Bolt", f"{result.bolt.shear_per_bolt:.1f} N")
        bb2.metric("Max Tension", f"{result.bolt.max_tension:.1f} N")
        bb3.metric("Bolt FoS", f"{result.bolt.bolt_fos:.2f}")
        bb4.metric("Utilization", f"{result.bolt.combined_utilization:.0%}")

    # Engineering interpretation
    st.divider()

    if result.controlling == "plate_bending":
        advice = (
            "**Plate bending** controls this design. Bending stiffness scales "
            "with thickness cubed (I ~ t^3), so increasing plate thickness is "
            "the most effective change. Switching to a higher-strength material "
            "will also help. Changing bolt parameters will not reduce plate stress."
        )
    elif result.controlling == "bolt":
        advice = (
            "The **bolt group** controls this design. Consider:\n"
            "- Larger bolt diameter (reduces shear and tension stress)\n"
            "- More bolts (distributes shear, increases moment arm sum)\n"
            "- Greater vertical spacing (increases moment resistance)\n\n"
            "Increasing plate thickness will not help bolt stresses."
        )
    elif result.controlling == "deflection":
        advice = (
            "**Deflection** controls this design. Plate stiffness scales with "
            "thickness cubed and material modulus E. Consider:\n"
            "- Thicker plate (strongest effect)\n"
            "- Stiffer material (higher E)\n"
            "- Shorter load offset"
        )
    else:
        advice = "Design is within all limits."

    if result.safe:
        st.success(advice)
    else:
        st.warning(advice)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE DESIGNS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:

    # ── Winners summary ───────────────────────────────────────────────────────
    st.subheader("Beam Winners")
    safe_beams = df[df["safe"]]
    if safe_beams.empty:
        st.warning("No safe beam designs. Adjust parameters in the Beam Optimizer tab.")
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

    # ── Top 5 tables ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Top 5 Safe Beams")

    if not safe_beams.empty:
        safe_fmt = safe_beams.copy()
        safe_fmt["Stress (MPa)"] = safe_fmt["stress"] / 1e6
        safe_fmt["Defl (mm)"] = safe_fmt["deflection"] * 1e3
        show = ["material", "section", "dims", "fos", "Stress (MPa)",
                "Defl (mm)", "weight", "cost"]

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.caption("By Weight (lightest)")
            st.dataframe(safe_fmt.nsmallest(5, "weight")[show],
                         width="stretch", hide_index=True)
        with tc2:
            st.caption("By Cost (cheapest)")
            st.dataframe(safe_fmt.nsmallest(5, "cost")[show],
                         width="stretch", hide_index=True)
        with tc3:
            st.caption("By FoS (safest)")
            st.dataframe(safe_fmt.nlargest(5, "fos")[show],
                         width="stretch", hide_index=True)

    # ── Bracket summary ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Bracket Summary")

    if "result" not in dir():
        st.info("Configure the Bracket Analysis tab to see results here.")
    else:
        bs1, bs2, bs3, bs4, bs5 = st.columns(5)
        bs1.metric("Overall FoS", f"{result.overall_fos:.2f}")
        bs2.metric("Plate Stress", f"{result.plate_stress / 1e6:.1f} MPa")
        bs3.metric("Bolt FoS", f"{result.bolt.bolt_fos:.2f}")
        bs4.metric("Controls", result.controlling.replace("_", " ").title())
        if result.safe:
            bs5.success("SAFE")
        else:
            bs5.error("UNSAFE")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ASSUMPTIONS & LIMITATIONS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_assumptions:

    st.info(
        "MechOpt is a **first-pass screening tool**. It is not a substitute "
        "for formal engineering analysis, detailed FEA, or professional review."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("What IS Modeled")
        st.markdown("""
- Linear-elastic material behaviour (Hooke's law)
- Static point loads only
- Small-deflection Euler-Bernoulli beam theory
- Prismatic (constant cross-section) beams
- Yielding-based factor of safety
- Simplified cantilever plate model for brackets
- Linear elastic bolt group load distribution
- Direct shear equally distributed among bolts
- Moment-induced bolt tension from centroid distance
        """)

        st.subheader("Material Data")
        st.markdown("""
- Nominal room-temperature properties for typical grades
- Cost figures are rough order-of-magnitude
- Treat cost comparisons as **relative**, not absolute
        """)

    with col_b:
        st.subheader("What is NOT Modeled")
        st.markdown("""
**Beam:**
- Buckling (lateral-torsional or local)
- Stress concentrations (holes, notches, fillets)
- Fatigue or cyclic loading
- Shear deflection
- Dynamic or impact loads
- Weld or joint effects
- Thermal effects
- Combined loading (axial + bending + torsion)

**Bracket:**
- Weld design
- Stress concentrations at bolt holes
- Bearing, tear-out, or block shear
- Prying action
- Plate buckling
- Bolt preload / thread engagement
- FEA-level stress distribution

**General:**
- Corrosion / environmental degradation
- Non-linear material behaviour
- Large-deflection effects
        """)

    st.warning(
        "Do not use this tool as the sole basis for manufacturing or "
        "safety-critical design decisions. All results should be verified "
        "by a qualified engineer before use in any real application."
    )

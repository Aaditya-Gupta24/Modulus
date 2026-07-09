"""Live bracket diagram — SVG builder for the Bracket Analysis visual canvas.

Pure-Python string builder, no external dependencies. This module is UI-only:
every number it draws (offset, load, bolt count/spacing, controlling check)
must be passed in by the caller from already-computed engine output
(`evaluate_bracket` in bracket.py). It never computes stress, FoS, or bolt
loads itself.

Bolt geometry note: `evaluate_bracket` lays bolts out on a single vertical
line, symmetric about the plate centroid —
    y_i = (i - (n-1)/2) * bolt_spacing_v
— and does NOT return per-bolt load values (only aggregate shear_per_bolt /
max_tension / combined_utilization on the BoltResult). Since moment-induced
bolt tension is proportional to distance from the centroid (T_i = M*r_i / sum(r^2)),
the "worst" bolt for a moment-loaded bracket is always the bolt farthest from
the centroid line. This module reconstructs that same 1-D symmetric layout
from (bolt_count, bolt_spacing) purely for drawing, and marks the farthest
bolt(s) as worst — it does not add a new engine calculation, just visualizes
the geometry the engine already assumes.

Colors come from `_palette` (mirrors the app `:root` CSS variables) so the
two diagrams match.
"""

from __future__ import annotations

from ._palette import (
    ACCENT, AMBER, BORDER_LIGHT, CYAN, MUTED, RED, SURFACE, TEXT,
    WALL_FILL, WALL_HATCH,
)


def render_bracket_svg(
    load_n: float,
    offset_m: float,
    plate_width_m: float,
    plate_thickness_m: float,
    bolt_count: int,
    bolt_spacing_m: float,
    controlling_constraint: str | None = None,
    worst_bolt_index: int | None = None,
    safe: bool | None = None,
    width: int = 640,
    height: int = 300,
) -> str:
    """Return a self-contained SVG string of the bracket diagram.

    Draws a side view (wall, cantilever arm, load arrow, offset dimension
    with an `M = P * e` annotation) stacked above a front view (plate outline
    with the bolt group laid out from bolt_count/bolt_spacing_m, worst bolt
    highlighted).

    Parameters
    ----------
    load_n:
        Applied load in newtons — label only.
    offset_m:
        Load offset from the wall in metres — drives the side-view arm
        length and the `M = P*e` label.
    plate_width_m, plate_thickness_m:
        Plate geometry in metres, used only to keep the front-view plate
        outline roughly proportioned and to size the bolt group footprint.
    bolt_count:
        Number of bolts (drawn on a single vertical line, matching the
        engine's bolt layout assumption).
    bolt_spacing_m:
        Vertical spacing between bolts in metres (for proportioning only —
        the on-screen spacing is normalized to fit the canvas).
    controlling_constraint:
        One of "plate_bending" / "bolt" / "bearing" / "tearout" /
        "deflection" (from BracketResult.controlling) — used to badge which
        view (plate vs bolt group) is the active constraint.
    worst_bolt_index:
        If given, highlight this bolt (0-indexed) instead of auto-computing
        the farthest-from-centroid bolt. If None, the module computes it
        from geometry (see module docstring — this is a drawing-only
        reconstruction of the engine's known symmetric bolt layout, not a
        new physics calculation).
    safe:
        Overall safe/unsafe flag (BracketResult.safe) — colors the load
        arrow / summary badge red when unsafe, matching the beam canvas
        pass/fail convention.
    width, height:
        Overall SVG canvas size in px.

    Returns
    -------
    str: a complete <svg>...</svg> string suitable for st.markdown(...,
    unsafe_allow_html=True).
    """
    # ── Determine worst bolt (farthest from centroid) purely for drawing ──
    # Same 1-D symmetric layout used internally by evaluate_bracket():
    # y_i = (i - (n-1)/2) * bolt_spacing_v
    n_bolts = max(int(bolt_count), 1)
    spacing = bolt_spacing_m or 0.01
    positions = [(i - (n_bolts - 1) / 2) * spacing for i in range(n_bolts)]
    if worst_bolt_index is None:
        worst_bolt_index = max(range(n_bolts), key=lambda i: abs(positions[i]))

    load_color = RED  # applied load is always drawn red
    ctrl = controlling_constraint or ""

    # ── Layout: side view (top half) + front view (bottom half) ──────────
    side_h = height * 0.46
    front_y0 = side_h + 14
    front_h = height - front_y0 - 10

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="display:block;height:auto;aspect-ratio:{width}/{height};'
        f'background:{SURFACE};border-radius:10px;">'
    ]
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{SURFACE}"/>')

    # ═══════════════════════ SIDE VIEW ═══════════════════════════════════
    parts.append(
        f'<text x="20" y="20" font-size="12" font-weight="700" fill="{TEXT}" '
        f'font-family="Inter,sans-serif">Side view — offset moment</text>'
    )

    wall_x = 30
    arm_y = side_h * 0.55
    arm_x1 = width - 70

    # Wall (hatched)
    parts.append(
        f'<rect x="{wall_x-16:.1f}" y="{arm_y-40:.1f}" width="16" height="90" '
        f'fill="{WALL_FILL}" stroke="{WALL_HATCH}" stroke-width="1.4"/>'
    )
    for hy in range(6):
        yy = arm_y - 38 + hy * 86 / 5
        parts.append(
            f'<line x1="{wall_x-16:.1f}" y1="{yy:.1f}" x2="{wall_x-4:.1f}" '
            f'y2="{yy+8:.1f}" stroke="{WALL_HATCH}" stroke-width="1"/>'
        )
    parts.append(
        f'<line x1="{wall_x:.1f}" y1="{arm_y-40:.1f}" x2="{wall_x:.1f}" '
        f'y2="{arm_y+50:.1f}" stroke="{TEXT}" stroke-width="2"/>'
    )

    # Bracket arm (cantilever) — plate-bending controlling emphasis
    arm_stroke = AMBER if ctrl == "plate_bending" else ACCENT
    arm_fill = "rgba(251,191,36,0.18)" if ctrl == "plate_bending" else "rgba(46,100,209,0.2)"
    parts.append(
        f'<rect x="{wall_x:.1f}" y="{arm_y-6:.1f}" width="{arm_x1-wall_x:.1f}" '
        f'height="12" rx="2" fill="{arm_fill}" stroke="{arm_stroke}" stroke-width="1.6"/>'
    )

    # Load arrow at the offset end
    parts.append(
        f'<line x1="{arm_x1:.1f}" y1="{arm_y-34:.1f}" x2="{arm_x1:.1f}" '
        f'y2="{arm_y-7:.1f}" stroke="{load_color}" stroke-width="2.4"/>'
    )
    parts.append(
        f'<polygon points="{arm_x1-6:.1f},{arm_y-15:.1f} {arm_x1+6:.1f},{arm_y-15:.1f} '
        f'{arm_x1:.1f},{arm_y-4:.1f}" fill="{load_color}"/>'
    )
    parts.append(
        f'<text x="{arm_x1:.1f}" y="{arm_y-40:.1f}" text-anchor="middle" '
        f'font-size="12.5" font-weight="700" fill="{load_color}" '
        f'font-family="Inter,sans-serif">P = {load_n:,.0f} N</text>'
    )

    # Offset dimension line + M = P*e annotation
    dim_y = arm_y + 26
    parts.append(
        f'<line x1="{wall_x:.1f}" y1="{dim_y:.1f}" x2="{arm_x1:.1f}" y2="{dim_y:.1f}" '
        f'stroke="{MUTED}" stroke-width="1" stroke-dasharray="4,3"/>'
    )
    parts.append(
        f'<line x1="{wall_x:.1f}" y1="{dim_y-5:.1f}" x2="{wall_x:.1f}" y2="{dim_y+5:.1f}" '
        f'stroke="{MUTED}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{arm_x1:.1f}" y1="{dim_y-5:.1f}" x2="{arm_x1:.1f}" y2="{dim_y+5:.1f}" '
        f'stroke="{MUTED}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{(wall_x+arm_x1)/2:.1f}" y="{dim_y+17:.1f}" text-anchor="middle" '
        f'font-size="11" fill="{MUTED}" font-style="italic">e = {offset_m*1000:.0f} mm</text>'
    )

    moment_nm = load_n * offset_m
    parts.append(
        f'<text x="{(wall_x+arm_x1)/2:.1f}" y="{dim_y+34:.1f}" text-anchor="middle" '
        f'font-size="12" font-weight="700" fill="{CYAN}" font-family="Inter,sans-serif">'
        f'M = P&middot;e = {moment_nm:,.1f} N&middot;m</text>'
    )

    # ═══════════════════════ FRONT VIEW ═══════════════════════════════════
    parts.append(
        f'<line x1="0" y1="{front_y0-6:.1f}" x2="{width}" y2="{front_y0-6:.1f}" '
        f'stroke="{BORDER_LIGHT}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="20" y="{front_y0+14:.1f}" font-size="12" font-weight="700" '
        f'fill="{TEXT}" font-family="Inter,sans-serif">Front view — plate + bolt group</text>'
    )

    plate_cx = width / 2
    plate_top = front_y0 + 28
    plate_h = front_h - 36
    plate_w = min(width * 0.34, 160)
    plate_x0 = plate_cx - plate_w / 2

    plate_stroke = AMBER if ctrl == "plate_bending" else ACCENT
    plate_fill = "rgba(251,191,36,0.14)" if ctrl == "plate_bending" else "rgba(46,100,209,0.14)"
    parts.append(
        f'<rect x="{plate_x0:.1f}" y="{plate_top:.1f}" width="{plate_w:.1f}" '
        f'height="{plate_h:.1f}" rx="4" fill="{plate_fill}" stroke="{plate_stroke}" '
        f'stroke-width="1.8"/>'
    )

    # Centroid line (dashed) — reference for "farthest from centroid" bolt
    centroid_y = plate_top + plate_h / 2
    parts.append(
        f'<line x1="{plate_x0+6:.1f}" y1="{centroid_y:.1f}" x2="{plate_x0+plate_w-6:.1f}" '
        f'y2="{centroid_y:.1f}" stroke="{MUTED}" stroke-width="0.8" '
        f'stroke-dasharray="3,3" opacity="0.6"/>'
    )

    # Map bolt normalized y-positions onto the plate height (with margin)
    max_abs = max(abs(p) for p in positions) or 1.0
    usable_half_h = (plate_h / 2) * 0.72
    bolt_ctrl_emph = ctrl in ("bolt", "bearing", "tearout")
    bolt_r = 6.5

    for i, y_off in enumerate(positions):
        norm = y_off / max_abs
        by = centroid_y + norm * usable_half_h
        is_worst = (i == worst_bolt_index) and n_bolts > 1
        if is_worst:
            fill = RED if bolt_ctrl_emph else AMBER
            stroke = "#b91c1c" if bolt_ctrl_emph else "#d97706"
            r = bolt_r + 1.5
        else:
            fill = AMBER
            stroke = "#d97706"
            r = bolt_r
        parts.append(
            f'<circle cx="{plate_cx:.1f}" cy="{by:.1f}" r="{r:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>'
        )
        if is_worst:
            parts.append(
                f'<circle cx="{plate_cx:.1f}" cy="{by:.1f}" r="{r+4:.1f}" '
                f'fill="none" stroke="{fill}" stroke-width="1.2" '
                f'stroke-dasharray="2,2" opacity="0.8"/>'
            )

    if n_bolts > 1:
        parts.append(
            f'<text x="{plate_x0+plate_w+14:.1f}" y="{centroid_y-usable_half_h:.1f}" '
            f'font-size="10.5" fill="{RED if bolt_ctrl_emph else AMBER}" '
            f'font-weight="700" font-family="Inter,sans-serif">'
            f'&#9679; worst bolt</text>'
        )
        parts.append(
            f'<text x="{plate_x0+plate_w+14:.1f}" y="{centroid_y-usable_half_h+14:.1f}" '
            f'font-size="9.5" fill="{MUTED}" font-family="Inter,sans-serif">'
            f'(farthest from centroid)</text>'
        )

    # Controlling-constraint badge (front view, top-right)
    if ctrl:
        ctrl_label = ctrl.replace("_", " ").title()
        badge_color = RED if (safe is False) else AMBER
        parts.append(
            f'<text x="{width-20:.1f}" y="{front_y0+14:.1f}" text-anchor="end" '
            f'font-size="11" font-weight="700" fill="{badge_color}" '
            f'font-family="Inter,sans-serif">controls: {ctrl_label}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)

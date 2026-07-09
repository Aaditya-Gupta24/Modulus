"""Live beam diagram — SVG builder for the Beam Optimizer visual canvas.

Pure-Python string builder, no external dependencies. This module is UI-only:
every number it draws (length, load, deflection, stress ratio) must be passed
in by the caller from the already-computed engine output. It never computes
stress, deflection, or FoS itself.

Colors come from `_palette` (mirrors the app `:root` CSS variables).
Stress gradient (low -> high): blue -> green -> yellow -> orange -> red.
"""

from __future__ import annotations

import math

from ._palette import (
    ACCENT, AMBER, BORDER_LIGHT, CARD, CYAN, GREEN, MUTED, RED, SURFACE,
    TEXT, WALL_FILL, WALL_HATCH,
)

STRESS_GRADIENT = [ACCENT, GREEN, AMBER, "#fb923c", RED]

_CANTILEVER_CASES = {"cantilever_end", "cantilever_udl"}
_UDL_CASES = {"cantilever_udl", "simply_udl"}

_LOAD_CASE_LABELS = {
    "cantilever_end": "Cantilever — Point Load",
    "cantilever_udl": "Cantilever — UDL",
    "simply_center": "Simply Supported — Point Load",
    "simply_udl": "Simply Supported — UDL",
}


def _section_thumb(section_name: str, cx: float, cy: float, s: float) -> str:
    """Small inline section glyph drawn directly on the beam canvas."""
    sk = ACCENT
    fl = "rgba(46,100,209,0.22)"
    name = (section_name or "").lower()
    if "circle" in name and "hollow" not in name:
        r = s * 0.42
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="1.6"/>')
    if name == "hollow_circle":
        ro, ri = s * 0.42, s * 0.26
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ro:.1f}" fill="{fl}" '
                f'stroke="{sk}" stroke-width="1.6"/>'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ri:.1f}" fill="{CARD}" '
                f'stroke="{sk}" stroke-width="1.2"/>')
    if name == "i_beam":
        bw, bh = s * 0.9, s * 1.0
        tf, tw = s * 0.18, s * 0.2
        x0, y0 = cx - bw / 2, cy - bh / 2
        return (f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{tf:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="1.4"/>'
                f'<rect x="{cx-tw/2:.1f}" y="{y0+tf:.1f}" width="{tw:.1f}" '
                f'height="{bh-2*tf:.1f}" fill="{fl}" stroke="{sk}" stroke-width="1.4"/>'
                f'<rect x="{x0:.1f}" y="{y0+bh-tf:.1f}" width="{bw:.1f}" height="{tf:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="1.4"/>')
    if name == "square_tube":
        o = s * 1.0
        wall = s * 0.16
        i = o - 2 * wall
        return (f'<rect x="{cx-o/2:.1f}" y="{cy-o/2:.1f}" width="{o:.1f}" height="{o:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="1.4"/>'
                f'<rect x="{cx-i/2:.1f}" y="{cy-i/2:.1f}" width="{i:.1f}" height="{i:.1f}" '
                f'fill="{CARD}" stroke="{sk}" stroke-width="1.1"/>')
    if name == "hollow_rectangle":
        ow, oh = s * 0.9, s * 1.0
        wall = s * 0.14
        iw, ih = ow - 2 * wall, oh - 2 * wall
        return (f'<rect x="{cx-ow/2:.1f}" y="{cy-oh/2:.1f}" width="{ow:.1f}" '
                f'height="{oh:.1f}" fill="{fl}" stroke="{sk}" stroke-width="1.4"/>'
                f'<rect x="{cx-iw/2:.1f}" y="{cy-ih/2:.1f}" width="{iw:.1f}" '
                f'height="{ih:.1f}" fill="{CARD}" stroke="{sk}" stroke-width="1.1"/>')
    # default: rectangle
    w, h = s * 0.9, s * 1.0
    return (f'<rect x="{cx-w/2:.1f}" y="{cy-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fl}" stroke="{sk}" stroke-width="1.6"/>')


def _stress_color(t: float) -> str:
    """Map a 0..1 position along the gradient stops to an interpolated hex color."""
    t = max(0.0, min(1.0, t))
    n = len(STRESS_GRADIENT) - 1
    pos = t * n
    i = min(int(pos), n - 1)
    frac = pos - i
    c0 = STRESS_GRADIENT[i].lstrip("#")
    c1 = STRESS_GRADIENT[i + 1].lstrip("#")
    r0, g0, b0 = int(c0[0:2], 16), int(c0[2:4], 16), int(c0[4:6], 16)
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r = round(r0 + (r1 - r0) * frac)
    g = round(g0 + (g1 - g0) * frac)
    b = round(b0 + (b1 - b0) * frac)
    return f"#{r:02x}{g:02x}{b:02x}"


def render_beam_svg(
    load_case: str,
    length_m: float,
    load_n: float,
    section_name: str,
    material_name: str,
    max_deflection_m: float | None = None,
    deflection_limit_m: float | None = None,
    stress_ratio: float | None = None,
    width: int = 640,
    height: int = 260,
) -> str:
    """Return a self-contained SVG string of the beam diagram.

    Parameters
    ----------
    load_case:
        One of "cantilever_end", "cantilever_udl", "simply_center", "simply_udl".
    length_m:
        Span length in metres (for the dimension label only — the drawing
        itself always uses a fixed on-screen span for legibility).
    load_n:
        Applied load in newtons (point load) or total distributed load (UDL),
        for the load label only.
    section_name:
        Cross-section type key (e.g. "i_beam", "circle") — drives the small
        section glyph drawn on the beam.
    material_name:
        Display name of the material, shown as an annotation.
    max_deflection_m:
        If provided (and > 0), draws an exaggerated deflected-shape overlay
        and a pass/fail badge (requires deflection_limit_m to know the limit;
        if the limit is None the badge just reports the value, no pass/fail).
    deflection_limit_m:
        The deflection constraint used to color the pass/fail badge.
    stress_ratio:
        0..1 value (stress / yield or utilisation) used to color the stress
        band along the beam and to place the peak near the wall (cantilever)
        or midspan (simply supported). If None, no stress band is drawn.
    width, height:
        Overall SVG canvas size in px.

    Returns
    -------
    str: a complete <svg>...</svg> string suitable for st.markdown(...,
    unsafe_allow_html=True) or components.html(...).
    """
    is_cantilever = load_case in _CANTILEVER_CASES
    is_udl = load_case in _UDL_CASES

    # ── Layout geometry ──────────────────────────────────────────────────
    margin_l, margin_r = 56, 56
    beam_y = height * 0.42
    span_x0 = margin_l + (34 if is_cantilever else 18)
    span_x1 = width - margin_r
    span_w = span_x1 - span_x0
    beam_h = 14

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="display:block;height:auto;aspect-ratio:{width}/{height};'
        f'background:{SURFACE};border-radius:10px;">'
    ]

    # ── Background grid (subtle) ─────────────────────────────────────────
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{SURFACE}"/>')

    # ── Load-case label (top-left) ───────────────────────────────────────
    lc_label = _LOAD_CASE_LABELS.get(load_case, load_case)
    parts.append(
        f'<text x="{margin_l}" y="24" font-size="12.5" font-weight="700" '
        f'fill="{TEXT}" font-family="Inter,sans-serif">{lc_label}</text>'
    )

    # ── Stress color band along the beam (optional) ──────────────────────
    if stress_ratio is not None:
        n_seg = 40
        seg_w = span_w / n_seg
        for i in range(n_seg):
            xpos = i / (n_seg - 1)  # 0..1 along span
            if is_cantilever:
                # peak at the wall (x=0), decaying toward the free end
                local = (1.0 - xpos)
            else:
                # peak at midspan for simply-supported
                local = 1.0 - abs(xpos - 0.5) * 2.0
            intensity = max(0.0, min(1.0, local)) * max(0.0, min(1.0, stress_ratio))
            color = _stress_color(intensity)
            x = span_x0 + i * seg_w
            parts.append(
                f'<rect x="{x:.1f}" y="{beam_y:.1f}" width="{seg_w+0.6:.1f}" '
                f'height="{beam_h:.1f}" fill="{color}" opacity="0.92"/>'
            )
        # thin outline over the band
        parts.append(
            f'<rect x="{span_x0:.1f}" y="{beam_y:.1f}" width="{span_w:.1f}" '
            f'height="{beam_h:.1f}" fill="none" stroke="{BORDER_LIGHT}" stroke-width="1"/>'
        )
    else:
        # Plain beam line
        parts.append(
            f'<rect x="{span_x0:.1f}" y="{beam_y:.1f}" width="{span_w:.1f}" '
            f'height="{beam_h:.1f}" rx="2" fill="rgba(46,100,209,0.22)" '
            f'stroke="{ACCENT}" stroke-width="1.6"/>'
        )

    beam_mid_y = beam_y + beam_h / 2

    # ── Supports ──────────────────────────────────────────────────────────
    if is_cantilever:
        # Fixed wall on the left
        wall_x = span_x0 - 18
        parts.append(
            f'<rect x="{wall_x-14:.1f}" y="{beam_y-28:.1f}" width="14" '
            f'height="{beam_h+56:.1f}" fill="{WALL_FILL}" stroke="{WALL_HATCH}" stroke-width="1.4"/>'
        )
        for hy in range(0, 6):
            yy = beam_y - 26 + hy * (beam_h + 52) / 5
            parts.append(
                f'<line x1="{wall_x-14:.1f}" y1="{yy:.1f}" x2="{wall_x-2:.1f}" '
                f'y2="{yy+8:.1f}" stroke="{WALL_HATCH}" stroke-width="1"/>'
            )
        parts.append(
            f'<line x1="{wall_x:.1f}" y1="{beam_y-2:.1f}" x2="{wall_x:.1f}" '
            f'y2="{beam_y+beam_h+2:.1f}" stroke="{TEXT}" stroke-width="2"/>'
        )
    else:
        # Pin (triangle) at left, roller (triangle + circles) at right
        pin_x = span_x0
        roll_x = span_x1
        tri_h = 16
        parts.append(
            f'<polygon points="{pin_x-9:.1f},{beam_y+beam_h+tri_h:.1f} '
            f'{pin_x+9:.1f},{beam_y+beam_h+tri_h:.1f} {pin_x:.1f},{beam_y+beam_h:.1f}" '
            f'fill="{ACCENT}" opacity="0.85"/>'
        )
        parts.append(
            f'<line x1="{pin_x-13:.1f}" y1="{beam_y+beam_h+tri_h:.1f}" '
            f'x2="{pin_x+13:.1f}" y2="{beam_y+beam_h+tri_h:.1f}" '
            f'stroke="{MUTED}" stroke-width="2"/>'
        )
        parts.append(
            f'<polygon points="{roll_x-9:.1f},{beam_y+beam_h+tri_h:.1f} '
            f'{roll_x+9:.1f},{beam_y+beam_h+tri_h:.1f} {roll_x:.1f},{beam_y+beam_h:.1f}" '
            f'fill="{ACCENT}" opacity="0.85"/>'
        )
        for dx in (-6, 0, 6):
            parts.append(
                f'<circle cx="{roll_x+dx:.1f}" cy="{beam_y+beam_h+tri_h+6:.1f}" '
                f'r="3" fill="{MUTED}"/>'
            )
        parts.append(
            f'<line x1="{roll_x-13:.1f}" y1="{beam_y+beam_h+tri_h+11:.1f}" '
            f'x2="{roll_x+13:.1f}" y2="{beam_y+beam_h+tri_h+11:.1f}" '
            f'stroke="{MUTED}" stroke-width="2"/>'
        )

    # ── Load arrows ────────────────────────────────────────────────────────
    load_label = f"P = {load_n:,.0f} N"
    if is_udl:
        load_label = f"w = {load_n:,.0f} N (total)"
        n_arrows = 8
        for i in range(n_arrows):
            ax = span_x0 + span_w * (i + 0.5) / n_arrows
            parts.append(
                f'<line x1="{ax:.1f}" y1="{beam_y-26:.1f}" x2="{ax:.1f}" '
                f'y2="{beam_y-4:.1f}" stroke="{RED}" stroke-width="1.8"/>'
            )
            parts.append(
                f'<polygon points="{ax-4:.1f},{beam_y-9:.1f} {ax+4:.1f},{beam_y-9:.1f} '
                f'{ax:.1f},{beam_y-1:.1f}" fill="{RED}"/>'
            )
        parts.append(
            f'<line x1="{span_x0:.1f}" y1="{beam_y-26:.1f}" x2="{span_x1:.1f}" '
            f'y2="{beam_y-26:.1f}" stroke="{RED}" stroke-width="1.2" opacity="0.6"/>'
        )
        parts.append(
            f'<text x="{(span_x0+span_x1)/2:.1f}" y="{beam_y-32:.1f}" text-anchor="middle" '
            f'font-size="12" font-weight="700" fill="{RED}">{load_label}</text>'
        )
    else:
        if is_cantilever:
            ax = span_x1
        else:
            ax = (span_x0 + span_x1) / 2
        parts.append(
            f'<line x1="{ax:.1f}" y1="{beam_y-38:.1f}" x2="{ax:.1f}" '
            f'y2="{beam_y-4:.1f}" stroke="{RED}" stroke-width="2.4"/>'
        )
        parts.append(
            f'<polygon points="{ax-6:.1f},{beam_y-12:.1f} {ax+6:.1f},{beam_y-12:.1f} '
            f'{ax:.1f},{beam_y-1:.1f}" fill="{RED}"/>'
        )
        parts.append(
            f'<text x="{ax:.1f}" y="{beam_y-42:.1f}" text-anchor="middle" '
            f'font-size="13" font-weight="700" fill="{RED}">{load_label}</text>'
        )

    # ── Span dimension line ───────────────────────────────────────────────
    dim_y = beam_y + beam_h + 44
    parts.append(
        f'<line x1="{span_x0:.1f}" y1="{dim_y:.1f}" x2="{span_x1:.1f}" y2="{dim_y:.1f}" '
        f'stroke="{MUTED}" stroke-width="1" stroke-dasharray="4,3"/>'
    )
    parts.append(
        f'<line x1="{span_x0:.1f}" y1="{dim_y-5:.1f}" x2="{span_x0:.1f}" y2="{dim_y+5:.1f}" '
        f'stroke="{MUTED}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{span_x1:.1f}" y1="{dim_y-5:.1f}" x2="{span_x1:.1f}" y2="{dim_y+5:.1f}" '
        f'stroke="{MUTED}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{(span_x0+span_x1)/2:.1f}" y="{dim_y+18:.1f}" text-anchor="middle" '
        f'font-size="11.5" fill="{MUTED}" font-style="italic">L = {length_m:.3f} m</text>'
    )

    # ── Deflected-shape overlay (optional) ────────────────────────────────
    if max_deflection_m is not None and max_deflection_m > 0:
        # Fixed on-screen sag — the shape is illustrative; the caption carries
        # the real value.
        sag_px = 34.0

        n_pts = 40
        pts = []
        for i in range(n_pts + 1):
            xf = i / n_pts  # 0..1 along span
            x = span_x0 + xf * span_w
            if is_cantilever:
                # cubic cantilever shape: sag ~ (3*(x/L)^2 - (x/L)^3) normalized to 1 at tip
                shape = 3 * xf**2 - xf**3
                shape /= 2.0  # normalize to max 1.0 at xf=1
            else:
                # simply-supported: sag ~ sin curve-ish (parabolic approx), 0 at ends
                shape = math.sin(math.pi * xf)
            y = beam_mid_y + shape * sag_px
            pts.append(f"{x:.1f},{y:.1f}")
        path_d = "M " + " L ".join(pts)
        parts.append(
            f'<path d="{path_d}" fill="none" stroke="{CYAN}" stroke-width="2.2" '
            f'stroke-dasharray="5,4" opacity="0.9"/>'
        )

        defl_mm = max_deflection_m * 1e3
        if deflection_limit_m and deflection_limit_m > 0:
            limit_mm = deflection_limit_m * 1e3
            passed = max_deflection_m <= deflection_limit_m
            badge_color = GREEN if passed else RED
            badge_text = "PASS" if passed else "FAIL"
            defl_caption = (
                f'<tspan fill="{CYAN}">&delta;<sub></sub> = {defl_mm:.2f} mm</tspan>'
                f'<tspan fill="{MUTED}"> / limit {limit_mm:.1f} mm &middot; </tspan>'
                f'<tspan fill="{badge_color}" font-weight="700">{badge_text}</tspan>'
            )
        else:
            defl_caption = f'<tspan fill="{CYAN}">&delta; = {defl_mm:.2f} mm</tspan>'

        parts.append(
            f'<text x="{span_x1:.1f}" y="{beam_mid_y+sag_px+16:.1f}" text-anchor="end" '
            f'font-size="11.5" font-family="Inter,sans-serif">{defl_caption}</text>'
        )
        parts.append(
            f'<text x="{span_x1:.1f}" y="{beam_mid_y+sag_px+30:.1f}" text-anchor="end" '
            f'font-size="9.5" fill="{MUTED}" font-style="italic">'
            f'shape exaggerated for display</text>'
        )

    # ── Section thumbnail + material/section label (bottom strip) ────────
    thumb_cx, thumb_cy = margin_l + 12, height - 34
    parts.append(_section_thumb(section_name, thumb_cx, thumb_cy, 22))
    sec_label = (section_name or "").replace("_", " ").title()
    parts.append(
        f'<text x="{thumb_cx+22:.1f}" y="{thumb_cy-4:.1f}" font-size="12" '
        f'font-weight="700" fill="{TEXT}" font-family="Inter,sans-serif">{sec_label}</text>'
    )
    parts.append(
        f'<text x="{thumb_cx+22:.1f}" y="{thumb_cy+12:.1f}" font-size="11" '
        f'fill="{MUTED}" font-family="Inter,sans-serif">{material_name}</text>'
    )

    # ── Stress ratio badge (top-right) ────────────────────────────────────
    if stress_ratio is not None:
        pct = max(0.0, min(1.0, stress_ratio)) * 100
        badge_color = _stress_color(stress_ratio)
        parts.append(
            f'<text x="{span_x1:.1f}" y="24" text-anchor="end" font-size="11.5" '
            f'font-weight="700" fill="{badge_color}" font-family="Inter,sans-serif">'
            f'stress utilisation {pct:.0f}%</text>'
        )

    parts.append("</svg>")
    return "".join(parts)

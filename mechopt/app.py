"""Streamlit UI for MechOpt — Mechanical Design Screening Dashboard.

Run locally:  streamlit run app.py
"""

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from collections import Counter

from mechopt.beam import max_deflection, max_moment, max_stress, factor_of_safety
from mechopt.bracket import evaluate_bracket, compare_gussets, GUSSET_TYPES
from mechopt.components.section_editor import section_editor
from mechopt.decision import rank_candidates, pareto_front, knee_point, classify_infeasible, explain_winner
from mechopt.design_review import generate_review
from mechopt.failure_modes import Status
from mechopt.materials import MATERIALS
from mechopt.optimizer import evaluate_candidates, recommend
from mechopt.report import export_report_bytes
from mechopt.stock import nearest_buyable
from mechopt.sections import (
    circle, hollow_circle, hollow_rectangle, i_beam, rectangle, square_tube,
)

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="MechOpt", page_icon="⬡", layout="wide")

# ─── Constants ───────────────────────────────────────────────────────────────
ACCENT = "oklch(0.58 0.16 255)"
ACCENT_HEX = "#2e64d1"
MAT_CLR = {
    "Aluminum 6061-T6": "#3b82f6",
    "Steel A36":        "#6b7280",
    "PLA (3D print)":   "#10b981",
    "Titanium Ti-6Al-4V": "#8b5cf6",
    "Brass C360":       "#f59e0b",
    "ABS (3D print)":   "#ef4444",
}

PLOTLY_COLORS = list(MAT_CLR.values())


# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --accent: oklch(0.58 0.16 255);
  --accent-hex: #2e64d1;
  --bg: #0b0e14;
  --surface: #151921;
  --card: #1a1f2e;
  --border: #2a2f42;
  --border-light: #222738;
  --text: #e8eaf0;
  --muted: #8b90a0;
  --green: #34d399;
  --red: #f87171;
  --amber: #fbbf24;
  --radius: 10px;
  --radius-sm: 6px;
  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
/* ── Global reset ───────────────────────────────────── */
html, body, .stApp {
  font-family: var(--font) !important;
  background: var(--bg) !important;
  color: var(--text) !important;
}
* { font-family: var(--font) !important; }
#MainMenu, footer, header .stDeployButton { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.block-container {
  max-width: 1320px !important;
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
}
/* ── Sticky header ──────────────────────────────────── */
.mo-hdr {
  position: sticky; top: 0; z-index: 999;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 10px 0 10px;
  margin-bottom: 20px;
  display: flex; align-items: center; justify-content: space-between;
}
.mo-hdr-l { display: flex; align-items: center; gap: 12px; }
.mo-logo {
  width: 38px; height: 38px;
  background: var(--accent);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.mo-brand-name { font-size: 18px; font-weight: 800; color: var(--text); letter-spacing: -0.3px; }
.mo-brand-sub  { font-size: 12px; color: var(--muted); margin-top: 1px; }
.mo-chip {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 500;
  color: var(--muted);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 50px;
  padding: 5px 14px;
  white-space: nowrap;
}
.mo-chip-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); }
/* ── Tabs — underline style ─────────────────────────── */
div[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important; padding: 0 !important;
}
button[data-baseweb="tab"] {
  font-weight: 600 !important;
  font-size: 0.875rem !important;
  color: var(--muted) !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  padding: 12px 22px !important;
  background: transparent !important;
  transition: color 0.15s;
}
button[data-baseweb="tab"]:hover { color: var(--text) !important; }
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--accent-hex) !important;
  border-bottom-color: var(--accent-hex) !important;
}
div[data-baseweb="tab-highlight"] {
  background: var(--accent-hex) !important;
  height: 2px !important;
}
div[data-baseweb="tab-border"] { display: none !important; }
/* ── Cards ──────────────────────────────────────────── */
.card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 24px; margin-bottom: 16px;
}
.card-hd {
  font-size: 10.5px; font-weight: 700; color: var(--accent-hex);
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px;
}
/* ── Metric tiles ───────────────────────────────────── */
div[data-testid="stMetric"] {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 14px 16px;
}
div[data-testid="stMetric"] label {
  font-size: 0.67rem !important; color: var(--muted) !important;
  text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-size: 1.2rem !important; font-weight: 700 !important; color: var(--text) !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
  font-size: 0.72rem !important;
}
/* ── Badges ─────────────────────────────────────────── */
.badge {
  display: inline-block; padding: 4px 14px; border-radius: 50px;
  font-weight: 700; font-size: 0.73rem; letter-spacing: 0.4px;
}
.badge-safe   { background: rgba(52,211,153,0.15); color: var(--green); border: 1px solid rgba(52,211,153,0.3); }
.badge-unsafe { background: rgba(248,113,113,0.15); color: var(--red); border: 1px solid rgba(248,113,113,0.3); }
/* ── Recommendation card ────────────────────────────── */
.rec-card { padding: 24px; }
.rec-label {
  font-size: 10.5px; font-weight: 700; color: var(--accent-hex);
  text-transform: uppercase; letter-spacing: 1px;
  margin-bottom: 2px;
}
.rec-mat  { font-size: 1.45rem; font-weight: 800; color: var(--text); margin: 4px 0 2px; }
.rec-sec  { font-size: 0.88rem; color: var(--muted); }
.rec-body { display: flex; gap: 24px; align-items: flex-start; margin-top: 16px; }
.rec-svg  { flex: 0 0 104px; }
.rec-tiles { flex: 1; }
.rec-foot {
  margin-top: 16px; padding: 12px 16px;
  background: rgba(46,100,209,0.08); border-radius: var(--radius-sm);
  font-size: 0.84rem; color: var(--muted); line-height: 1.65;
}
.rec-foot strong { color: var(--text); }
/* ── No-safe banner ─────────────────────────────────── */
.no-safe {
  background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.25);
  border-radius: var(--radius); padding: 28px; text-align: center;
  margin-bottom: 16px;
}
.no-safe b  { display: block; font-size: 1.1rem; color: var(--red); margin-bottom: 8px; }
.no-safe p  { font-size: 0.85rem; color: #fca5a5; margin: 0; }
/* ── Callouts ───────────────────────────────────────── */
.callout {
  padding: 14px 18px; border-radius: var(--radius-sm);
  margin-bottom: 16px; font-size: 0.84rem; line-height: 1.6;
}
.callout-blue  { background: rgba(46,100,209,0.1);  color: #93b4f5; }
.callout-green { background: rgba(52,211,153,0.1); color: #6ee7b7; }
.callout-amber { background: rgba(251,191,36,0.1); color: #fcd34d; }
.callout-red   { background: rgba(248,113,113,0.1); color: #fca5a5; }
/* ── Tables ─────────────────────────────────────────── */
.mt {
  width: 100%; border-collapse: separate; border-spacing: 0;
  font-size: 0.82rem; border-radius: var(--radius-sm);
  overflow: hidden; border: 1px solid var(--border);
}
.mt th {
  background: var(--surface); padding: 10px 12px; text-align: left;
  font-weight: 700; color: var(--muted); font-size: 0.68rem;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.mt td {
  padding: 9px 12px; border-top: 1px solid var(--border-light); color: var(--text);
}
.mt .n { text-align: right; font-size: 0.8rem; font-variant-numeric: tabular-nums; }
.mt tr:hover td { background: rgba(46,100,209,0.04); }
.mt .row-safe td:first-child { border-left: 3px solid var(--green); }
.mt .row-fail td:first-child { border-left: 3px solid var(--red); }
/* ── Material dot ───────────────────────────────────── */
.mdot {
  display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; margin-right: 6px; vertical-align: middle;
}
/* ── Utilisation bar ────────────────────────────────── */
.ub { margin: 6px 0; }
.ub-lbl {
  display: flex; justify-content: space-between;
  font-size: 0.7rem; color: var(--muted); margin-bottom: 3px; font-weight: 600;
}
.ub-lbl .v { font-variant-numeric: tabular-nums; }
.ub-track {
  height: 6px; background: var(--surface); border-radius: 3px;
  overflow: hidden; border: 1px solid var(--border);
}
.ub-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
/* ── Rail heading (input panel) ─────────────────────── */
.rh {
  font-size: 10.5px; font-weight: 700; color: var(--accent-hex);
  text-transform: uppercase; letter-spacing: 1px;
  margin: 18px 0 10px; padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}
.rh:first-child { margin-top: 0; }
/* ── Priority pills (2x2) ──────────────────────────── */
.prio-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin: 8px 0;
}
.prio-pill-btn {
  padding: 9px 0; border: 1px solid var(--border); border-radius: var(--radius-sm);
  text-align: center; font-size: 0.82rem; font-weight: 600;
  color: var(--muted); cursor: default; transition: all 0.15s;
}
.prio-pill-btn.active {
  background: var(--accent-hex); color: #fff; border-color: var(--accent-hex);
}
/* ── Winner cards (Compare tab) ─────────────────────── */
.wgrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 12px 0; }
.wc {
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 16px; border-top: 3px solid var(--accent-hex);
  background: var(--card);
}
.wc-lbl {
  font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.6px; color: var(--muted); margin-bottom: 6px;
}
.wc-mat { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 2px; }
.wc-sec { font-size: 0.8rem; color: var(--muted); margin-bottom: 10px; }
.wc-row {
  display: flex; gap: 8px; flex-wrap: wrap;
  font-size: 0.72rem; color: var(--muted); font-variant-numeric: tabular-nums;
}
.wc-row b { color: var(--text); }
.wc.light  { border-top-color: #06b6d4; }
.wc.cheap  { border-top-color: var(--green); }
.wc.safe   { border-top-color: var(--amber); }
.wc.bal    { border-top-color: #8b5cf6; }
/* ── Prio pill (Compare table) ──────────────────────── */
.pp {
  display: inline-block; padding: 2px 10px; border-radius: 50px;
  font-size: 0.7rem; font-weight: 700;
}
.pp-bal    { background: rgba(139,92,246,0.15); color: #a78bfa; }
.pp-light  { background: rgba(6,182,212,0.15); color: #22d3ee; }
.pp-cheap  { background: rgba(52,211,153,0.15); color: var(--green); }
.pp-safe   { background: rgba(251,191,36,0.15); color: var(--amber); }
/* ── Assumption lists ───────────────────────────────── */
.al { list-style: none; padding: 0; margin: 0; }
.al li {
  padding: 5px 0 5px 18px; position: relative;
  font-size: 0.84rem; line-height: 1.55;
}
.al li::before {
  content: ""; position: absolute; left: 3px; top: 13px;
  width: 5px; height: 5px; border-radius: 50%;
}
.al.grn li::before { background: var(--green); }
.al.red li::before { background: var(--red); }
/* ── Section label in assumption card ───────────────── */
.asec {
  font-size: 0.75rem; font-weight: 700; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin: 14px 0 6px; padding-bottom: 4px;
  border-bottom: 1px solid var(--border-light);
}
.asec:first-child { margin-top: 0; }
/* ── Expanders ──────────────────────────────────────── */
details[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--card) !important;
}
details[data-testid="stExpander"] summary span { font-weight: 600 !important; }
/* ── Selectbox / multiselect ────────────────────────── */
div[data-baseweb="select"] * { font-family: var(--font) !important; }
/* ── Hide Streamlit heading anchors ─────────────────── */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { display: none; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def mdot(name):
    """Material color dot."""
    c = MAT_CLR.get(name, "#6b7280")
    return f'<span class="mdot" style="background:{c}"></span>'


def section_svg(sec_type, size=104):
    """Inline SVG thumbnail for a cross-section type."""
    s = size
    cx, cy = s / 2, s / 2
    sk = ACCENT_HEX
    fl = "rgba(46,100,209,0.2)"
    bg = "#1a1f2e"
    if sec_type == "rectangle":
        w, h = s * 0.5, s * 0.65
        return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
                f'<rect x="{cx-w/2:.1f}" y="{cy-h/2:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" fill="{fl}" stroke="{sk}" stroke-width="2" rx="2"/></svg>')
    if sec_type == "circle":
        r = s * 0.32
        return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
                f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{fl}" '
                f'stroke="{sk}" stroke-width="2"/></svg>')
    if sec_type == "i_beam":
        bw, bh = s * 0.55, s * 0.65
        tf, tw = s * 0.1, s * 0.12
        x0, y0 = cx - bw / 2, cy - bh / 2
        return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
                f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{tf:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="2" rx="1"/>'
                f'<rect x="{cx-tw/2:.1f}" y="{y0+tf:.1f}" width="{tw:.1f}" '
                f'height="{bh-2*tf:.1f}" fill="{fl}" stroke="{sk}" stroke-width="2"/>'
                f'<rect x="{x0:.1f}" y="{y0+bh-tf:.1f}" width="{bw:.1f}" height="{tf:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="2" rx="1"/></svg>')
    if sec_type == "square_tube":
        o = s * 0.6
        wall = s * 0.08
        i = o - 2 * wall
        return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
                f'<rect x="{cx-o/2:.1f}" y="{cy-o/2:.1f}" width="{o:.1f}" height="{o:.1f}" '
                f'fill="{fl}" stroke="{sk}" stroke-width="2" rx="2"/>'
                f'<rect x="{cx-i/2:.1f}" y="{cy-i/2:.1f}" width="{i:.1f}" height="{i:.1f}" '
                f'fill="{bg}" stroke="{sk}" stroke-width="1.5" rx="1"/></svg>')
    if sec_type == "hollow_rectangle":
        ow, oh = s * 0.5, s * 0.65
        wall = s * 0.07
        iw, ih = ow - 2 * wall, oh - 2 * wall
        return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
                f'<rect x="{cx-ow/2:.1f}" y="{cy-oh/2:.1f}" width="{ow:.1f}" '
                f'height="{oh:.1f}" fill="{fl}" stroke="{sk}" stroke-width="2" rx="2"/>'
                f'<rect x="{cx-iw/2:.1f}" y="{cy-ih/2:.1f}" width="{iw:.1f}" '
                f'height="{ih:.1f}" fill="{bg}" stroke="{sk}" stroke-width="1.5" rx="1"/></svg>')
    if sec_type == "hollow_circle":
        ro, ri = s * 0.32, s * 0.22
        return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
                f'<circle cx="{cx}" cy="{cy}" r="{ro:.1f}" fill="{fl}" '
                f'stroke="{sk}" stroke-width="2"/>'
                f'<circle cx="{cx}" cy="{cy}" r="{ri:.1f}" fill="{bg}" '
                f'stroke="{sk}" stroke-width="1.5"/></svg>')
    return ""


def bracket_svg():
    """Small schematic of bracket setup."""
    return (
        '<svg viewBox="0 0 260 140" width="260" height="140" '
        'style="display:block;margin:8px auto 0;">'
        # Wall hatching
        '<rect x="10" y="10" width="16" height="120" fill="#2a2f42" stroke="#4b5068" stroke-width="1.5"/>'
        '<line x1="12" y1="10" x2="12" y2="130" stroke="#4b5068" stroke-width="0.5" stroke-dasharray="3,3"/>'
        '<line x1="18" y1="10" x2="18" y2="130" stroke="#4b5068" stroke-width="0.5" stroke-dasharray="3,3"/>'
        '<line x1="24" y1="10" x2="24" y2="130" stroke="#4b5068" stroke-width="0.5" stroke-dasharray="3,3"/>'
        # Plate
        '<rect x="26" y="55" width="160" height="12" rx="2" fill="rgba(46,100,209,0.25)" stroke="#2e64d1" stroke-width="1.5"/>'
        # Bolts
        '<circle cx="40" cy="40" r="5" fill="#fbbf24" stroke="#d97706" stroke-width="1"/>'
        '<circle cx="40" cy="70" r="5" fill="#fbbf24" stroke="#d97706" stroke-width="1"/>'
        '<circle cx="40" cy="100" r="5" fill="#fbbf24" stroke="#d97706" stroke-width="1"/>'
        '<circle cx="40" cy="130" r="5" fill="#fbbf24" stroke="#d97706" stroke-width="1"/>'
        # Load arrow
        '<line x1="200" y1="20" x2="200" y2="52" stroke="#f87171" stroke-width="2"/>'
        '<polygon points="194,48 200,58 206,48" fill="#f87171"/>'
        '<text x="200" y="15" text-anchor="middle" font-size="12" font-weight="700" fill="#f87171">P</text>'
        # Dimension line for offset
        '<line x1="30" y1="78" x2="194" y2="78" stroke="#8b90a0" stroke-width="0.8" '
        'stroke-dasharray="4,3"/>'
        '<line x1="30" y1="74" x2="30" y2="82" stroke="#8b90a0" stroke-width="0.8"/>'
        '<line x1="194" y1="74" x2="194" y2="82" stroke="#8b90a0" stroke-width="0.8"/>'
        '<text x="112" y="92" text-anchor="middle" font-size="10" fill="#8b90a0" '
        'font-style="italic">offset e</text>'
        '</svg>')


def util_bar(label, value, max_val=1.0, invert=False):
    """Render a utilisation bar."""
    pct = min(value / max_val, 1.0) * 100 if max_val > 0 else 0
    if invert:
        color = "#34d399" if pct < 60 else ("#fbbf24" if pct < 85 else "#f87171")
    else:
        color = "#f87171" if pct < 40 else ("#fbbf24" if pct < 70 else "#34d399")
    return (
        f'<div class="ub">'
        f'<div class="ub-lbl"><span>{label}</span><span class="v">{pct:.0f}%</span></div>'
        f'<div class="ub-track">'
        f'<div class="ub-fill" style="width:{pct:.1f}%;background:{color};"></div>'
        f'</div></div>'
    )


PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#151921",
    font=dict(family="Inter, sans-serif", color="#8b90a0", size=12),
    margin=dict(l=50, r=16, t=40, b=50),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2a2f42",
                borderwidth=1, font=dict(size=11)),
    xaxis=dict(gridcolor="#1e2336", zeroline=False, linecolor="#2a2f42"),
    yaxis=dict(gridcolor="#1e2336", zeroline=False, linecolor="#2a2f42"),
    hoverlabel=dict(bgcolor="#1a1f2e", font_size=12, font_color="#e8eaf0",
                    bordercolor="#2a2f42"),
)


def scatter_plot(df, x_col, y_col, x_label, y_label, fos_target, title,
                 rec_row=None):
    """Dark-themed Plotly scatter with safe/unsafe split and target line."""
    safe_df = df[df["safe"]]
    unsafe_df = df[~df["safe"]]
    fig = go.Figure()
    if not unsafe_df.empty:
        fig.add_trace(go.Scatter(
            x=unsafe_df[x_col], y=unsafe_df[y_col], mode="markers",
            marker=dict(size=6, color="#3a3f52", opacity=0.5,
                        line=dict(width=0.5, color="#4b5068")),
            name="Unsafe",
            text=unsafe_df.apply(
                lambda r: f"{r['material']}<br>{r['section']} {r['dims']}"
                          f"<br>FoS {r['fos']:.2f}", axis=1),
            hoverinfo="text",
        ))
    materials = safe_df["material"].unique()
    for i, mat in enumerate(materials):
        mdf = safe_df[safe_df["material"] == mat]
        fig.add_trace(go.Scatter(
            x=mdf[x_col], y=mdf[y_col], mode="markers",
            marker=dict(size=8, color=MAT_CLR.get(mat, "#6b7280"),
                        line=dict(width=1, color="rgba(0,0,0,0.3)")),
            name=mat,
            text=mdf.apply(
                lambda r: f"<b>{r['material']}</b><br>{r['section']} {r['dims']}"
                          f"<br>FoS <b>{r['fos']:.2f}</b> · {r['stress']/1e6:.1f} MPa"
                          f"<br>{r['weight']:.4f} kg · ${r['cost']:.2f}", axis=1),
            hoverinfo="text",
        ))
    if rec_row is not None:
        fig.add_trace(go.Scatter(
            x=[rec_row[x_col]], y=[rec_row[y_col]], mode="markers",
            marker=dict(size=14, color="rgba(0,0,0,0)",
                        line=dict(width=2.5, color=ACCENT_HEX)),
            name="Recommended", showlegend=False, hoverinfo="skip",
        ))
    if y_col == "fos":
        fig.add_hline(y=fos_target, line_dash="dash", line_color="#f87171",
                      line_width=1, opacity=0.6,
                      annotation_text=f"Target FoS = {fos_target}",
                      annotation_position="top left",
                      annotation_font=dict(size=10, color="#f87171"))
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=title, font=dict(size=13)))
    fig.update_xaxes(title_text=x_label)
    fig.update_yaxes(title_text=y_label)
    return fig


def _design_label(row):
    """Compact label for a candidate row."""
    return f'{row["material"]} / {row["section"].replace("_", " ").title()} / {row["dims"]}'


def tradeoff_html(df, fos_target, deflection_limit=None):
    """Render beam tradeoff insight text from evaluated candidates."""
    n_total = len(df)
    if n_total == 0:
        return (
            '<div class="callout callout-amber">'
            '<strong>No candidates were generated.</strong> Add at least one material and '
            'one cross-section to populate the tradeoff space.'
            '</div>'
        )

    safe_df = df[df["safe"]]
    n_safe = len(safe_df)
    best_fos = df.loc[df["fos"].idxmax()]
    lightest_all = df.loc[df["weight"].idxmin()]
    cheapest_all = df.loc[df["cost"].idxmin()]

    def metric_tile(label, value, sub=""):
        return (
            '<div style="background:#151921;border:1px solid #2a2f42;'
            'border-radius:6px;padding:12px 14px;min-height:78px;">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;'
            f'color:#8b90a0;font-weight:700;">{label}</div>'
            f'<div style="font-size:18px;color:#e8eaf0;font-weight:800;margin-top:4px;">{value}</div>'
            f'<div style="font-size:12px;color:#8b90a0;margin-top:3px;">{sub}</div>'
            '</div>'
        )

    if safe_df.empty:
        closest = best_fos
        fos_gap = max(float(fos_target) - float(closest["fos"]), 0.0)
        defl_note = ""
        if deflection_limit:
            defl_ratio = closest["deflection"] / deflection_limit
            defl_note = f" Its deflection is {defl_ratio:.1f}x the limit."

        near = df.sort_values("fos", ascending=False).head(3)
        rows = ""
        for _, row in near.iterrows():
            rows += (
                '<tr>'
                f'<td>{_design_label(row)}</td>'
                f'<td class="n">{row["fos"]:.2f}</td>'
                f'<td class="n">{row["weight"]:.4f}</td>'
                f'<td class="n">${row["cost"]:.2f}</td>'
                f'<td class="n">{row["deflection"]*1e3:.2f}</td>'
                '</tr>'
            )

        safe_tile = metric_tile("Safe designs", f"0 / {n_total}",
                                "No feasible option yet")
        closest_tile = metric_tile("Closest FoS", f'{closest["fos"]:.2f}',
                                   f"gap {fos_gap:.2f}")
        lightest_tile = metric_tile("Lightest checked",
                                    f'{lightest_all["weight"]:.4f} kg',
                                    _design_label(lightest_all))
        cheapest_tile = metric_tile("Lowest cost checked",
                                    f'${cheapest_all["cost"]:.2f}',
                                    _design_label(cheapest_all))

        return (
            '<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
            'gap:10px;margin-bottom:14px;">'
            f'{safe_tile}{closest_tile}{lightest_tile}{cheapest_tile}'
            '</div>'
            '<div class="callout callout-amber">'
            f'<strong>Tradeoff read:</strong> the best strength candidate is {_design_label(closest)} '
            f'at FoS {closest["fos"]:.2f}, still short of the {float(fos_target):.1f} target.'
            f'{defl_note} Increase section depth, enable tube/I-beam sections, choose a stronger '
            'material, or relax the load/deflection requirement.'
            '</div>'
            '<table class="mt" style="margin-top:10px;"><thead><tr>'
            '<th>Closest candidates</th><th class="n">FoS</th><th class="n">kg</th>'
            '<th class="n">$</th><th class="n">defl mm</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )

    lightest = safe_df.loc[safe_df["weight"].idxmin()]
    cheapest = safe_df.loc[safe_df["cost"].idxmin()]
    strongest = safe_df.loc[safe_df["fos"].idxmax()]
    efficiency = safe_df["fos"] / safe_df["weight"]
    efficient = safe_df.loc[efficiency.idxmax()]
    safe_rate = 100 * n_safe / n_total
    weight_span = safe_df["weight"].max() / max(safe_df["weight"].min(), 1e-12)
    cost_span = safe_df["cost"].max() / max(safe_df["cost"].min(), 1e-12)

    rows = ""
    winners = [
        ("Lightest safe", lightest),
        ("Cheapest safe", cheapest),
        ("Strongest safe", strongest),
        ("Best FoS/kg", efficient),
    ]
    for label, row in winners:
        rows += (
            '<tr>'
            f'<td>{label}</td>'
            f'<td>{_design_label(row)}</td>'
            f'<td class="n">{row["fos"]:.2f}</td>'
            f'<td class="n">{row["weight"]:.4f}</td>'
            f'<td class="n">${row["cost"]:.2f}</td>'
            '</tr>'
        )

    safe_tile = metric_tile("Safe designs", f"{n_safe} / {n_total}",
                            f"{safe_rate:.0f}% feasible")
    lightest_tile = metric_tile("Lightest safe",
                                f'{lightest["weight"]:.4f} kg',
                                _design_label(lightest))
    cheapest_tile = metric_tile("Lowest cost",
                                f'${cheapest["cost"]:.2f}',
                                _design_label(cheapest))
    efficiency_tile = metric_tile("Best FoS/kg",
                                  f'{efficient["fos"]/efficient["weight"]:.1f}',
                                  _design_label(efficient))

    return (
        '<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        'gap:10px;margin-bottom:14px;">'
        f'{safe_tile}{lightest_tile}{cheapest_tile}{efficiency_tile}'
        '</div>'
        '<div class="callout callout-blue">'
        f'<strong>Tradeoff read:</strong> safe candidates span {weight_span:.1f}x in weight and '
        f'{cost_span:.1f}x in cost. {_design_label(efficient)} gives the strongest safety return '
        f'per kg, while {_design_label(lightest)} is the mass floor and {_design_label(strongest)} '
        'maximizes margin.'
        '</div>'
        '<table class="mt" style="margin-top:10px;"><thead><tr>'
        '<th>Objective</th><th>Candidate</th><th class="n">FoS</th>'
        '<th class="n">kg</th><th class="n">$</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def card(title=None):
    """Open a card container."""
    hd = f'<div class="card-hd">{title}</div>' if title else ""
    return f'<div class="card">{hd}'


CARD_END = "</div>"


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="mo-hdr">'
    '<div class="mo-hdr-l">'
    '<div class="mo-logo">'
    '<svg width="18" height="18" viewBox="0 0 18 18">'
    '<rect x="3" y="3" width="12" height="12" rx="1" transform="rotate(45 9 9)" '
    'fill="none" stroke="white" stroke-width="1.8"/>'
    '</svg></div>'
    '<div>'
    '<div class="mo-brand-name">MechOpt</div>'
    '<div class="mo-brand-sub">Mechanical design screening · first-pass static analysis</div>'
    '</div></div>'
    '<div class="mo-chip">'
    '<span class="mo-chip-dot"></span>SI units · static load'
    '</div></div>',
    unsafe_allow_html=True,
)


# ─── Tabs ────────────────────────────────────────────────────────────────────
tab_beam, tab_bracket, tab_compare, tab_assumptions = st.tabs([
    "Beam Optimizer", "Bracket Analysis", "Compare Designs", "Assumptions",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — BEAM OPTIMIZER
# ═════════════════════════════════════════════════════════════════════════════
with tab_beam:

    rail, results = st.columns([1, 3], gap="large")

    # ── Input rail ───────────────────────────────────────────────────────────
    with rail:
        st.markdown('<div class="rh" style="margin-top:0">Loading</div>',
                    unsafe_allow_html=True)
        load = st.number_input("Load P (N)", min_value=1.0, value=500.0,
                               step=50.0, key="b_load")
        length = st.number_input("Span L (m)", min_value=0.01, value=1.0,
                                 step=0.1, key="b_len")
        load_case = st.selectbox(
            "Load case",
            ["cantilever_end", "simply_center"],
            format_func=lambda x: {
                "cantilever_end": "Cantilever · end load",
                "simply_center": "Simply supported · center",
            }[x],
            key="b_lc",
        )
        fos_target = st.number_input("Target FoS", min_value=1.0, value=2.0,
                                     step=0.5, key="b_fos")
        defl_limit_mm = st.number_input(
            "Max deflection (mm)", min_value=0.0, value=0.0, step=0.5,
            help="0 = no limit", key="b_defl")
        deflection_limit = defl_limit_mm / 1000.0 if defl_limit_mm > 0 else None

        st.markdown('<div class="rh">Priority</div>', unsafe_allow_html=True)
        priority = st.radio(
            "Objective", ["balanced", "lightest", "cheapest", "safest"],
            format_func=str.title, horizontal=True, key="b_prio",
            label_visibility="collapsed",
        )

        st.markdown('<div class="rh">Materials</div>', unsafe_allow_html=True)
        mat_opts = {k: v.name for k, v in MATERIALS.items()}
        selected_mats = st.multiselect(
            "Materials", options=list(mat_opts.keys()),
            default=list(mat_opts.keys()),
            format_func=lambda k: mat_opts[k], key="b_mats",
            label_visibility="collapsed",
        )

        st.markdown('<div class="rh">Cross-sections</div>',
                    unsafe_allow_html=True)
        all_secs = ["rectangle", "circle", "i_beam", "square_tube",
                    "hollow_rectangle", "hollow_circle"]
        sec_labels = {
            "rectangle": "Rectangle", "circle": "Circle",
            "i_beam": "I-Beam", "square_tube": "Sq. Tube",
            "hollow_rectangle": "Box Tube", "hollow_circle": "Round Tube",
        }
        selected_secs = st.multiselect(
            "Sections", options=all_secs,
            default=["rectangle", "circle"],
            format_func=lambda s: sec_labels.get(s, s),
            key="b_secs", label_visibility="collapsed",
        )

        st.markdown('<div class="rh">Design mode</div>',
                    unsafe_allow_html=True)
        design_mode = st.radio(
            "Design mode",
            ["conceptual", "stock"],
            format_func=lambda x: {
                "conceptual": "Conceptual sweep",
                "stock": "Standard stock only",
            }[x],
            horizontal=True, key="b_design_mode",
            label_visibility="collapsed",
        )
        use_stock = design_mode == "stock"

    if not selected_mats:
        selected_mats = list(MATERIALS.keys())
    if not selected_secs:
        selected_secs = ["rectangle", "circle"]

    # ── Evaluate ─────────────────────────────────────────────────────────────
    try:
        df = evaluate_candidates(
            float(load), float(length), str(load_case), float(fos_target),
            material_keys=list(selected_mats),
            section_types=list(selected_secs),
            deflection_limit=float(deflection_limit) if deflection_limit else None,
            stock_mode=use_stock,
        )
    except Exception as e:
        with results:
            st.error(f"Evaluation error: {e}")
        st.stop()

    safe_df = df[df["safe"]]
    n_total = len(df)
    n_safe = len(safe_df)

    # ── Results column ───────────────────────────────────────────────────────
    with results:

        # 1. Recommendation card ──────────────────────────────────────────────
        tradeoff_feedback = (
            '<div class="rec-foot">'
            'No safe design is selected yet. The tradeoff space below shows the '
            'closest candidates and the main changes that would move the design '
            'toward feasibility.'
            '</div>'
        )
        if safe_df.empty:
            st.markdown(
                f'<div class="no-safe">'
                f'<b>No safe design among {n_total} candidates</b>'
                f'<p>Try reducing the load, lowering the target FoS, adding more '
                f'materials or sections, or removing the deflection limit.</p></div>',
                unsafe_allow_html=True,
            )
            rec = None
        else:
            rec = recommend(df, priority)
            _mat_key = [k for k, v in MATERIALS.items()
                        if v.name == rec["material"]][0]
            _mat = MATERIALS[_mat_key]

            sc = rec["safety_case"]
            controlling = sc.controlling_check.replace("_", " ").title()

            badge_cls = "badge-safe" if rec["safe"] else "badge-unsafe"
            badge_txt = "SAFE" if rec["safe"] else "UNSAFE"
            svg_html = section_svg(rec["section"])

            defl_str = f'{rec["deflection"]*1e3:.2f} mm'
            if deflection_limit:
                defl_str += f" (limit {defl_limit_mm:.1f} mm)"

            st.markdown(
                f'<div class="card rec-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'<div>'
                f'<div class="rec-label">Recommended · {priority.title()}</div>'
                f'<div class="rec-mat">{rec["material"]}</div>'
                f'<div class="rec-sec">{rec["section"].replace("_"," ").title()} · '
                f'{rec["dims"]}</div>'
                f'</div>'
                f'<span class="badge {badge_cls}">{badge_txt}</span>'
                f'</div>'
                f'<div class="rec-body">'
                f'<div class="rec-svg">{svg_html}</div>'
                f'<div class="rec-tiles" style="flex:1;">'
                f'</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Metric tiles
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            delta_fos = rec["fos"] - fos_target
            fos_color = "normal" if delta_fos >= 0 else "inverse"
            m1.metric("Factor of Safety", f"{rec['fos']:.2f}",
                      delta=f"{delta_fos:+.2f} vs target",
                      delta_color=fos_color)
            m2.metric("Max Stress",
                      f"{rec['stress']/1e6:.1f} MPa",
                      delta=f"σy = {_mat.sigma_y/1e6:.0f} MPa",
                      delta_color="off")
            m3.metric("Deflection",
                      f"{rec['deflection']*1e3:.2f} mm",
                      delta=f"limit {defl_limit_mm:.1f} mm" if deflection_limit else "no limit",
                      delta_color="off")
            m4.metric("Weight", f"{rec['weight']:.4f} kg")
            m5.metric("Cost", f"${rec['cost']:.2f}")
            m6.metric("Controls", controlling)

            # Utilisation bars
            bars = util_bar("Stress utilisation",
                            rec["stress"] / _mat.sigma_y if _mat.sigma_y else 0,
                            invert=True)
            if deflection_limit and deflection_limit > 0:
                bars += util_bar("Deflection utilisation",
                                 rec["deflection"] / deflection_limit,
                                 invert=True)
            st.markdown(bars, unsafe_allow_html=True)

            # Failure-mode safety-case table
            fm_html = card("Failure-mode safety case")
            fm_html += '<table class="mt"><thead><tr>'
            fm_html += ('<th>Check</th><th>Value</th><th>Limit</th>'
                        '<th class="n">Margin</th><th>Status</th>')
            fm_html += '</tr></thead><tbody>'
            for chk in sc.checks:
                is_ctrl = chk.name == sc.controlling_check
                row_style = (' style="font-weight:700;border-left:3px solid '
                             'var(--accent-hex);"' if is_ctrl else '')
                td_pre = '<td style="font-weight:700;">' if is_ctrl else '<td>'
                td_n_pre = '<td class="n" style="font-weight:700;">' if is_ctrl else '<td class="n">'

                check_label = chk.name.replace("_", " ").title()

                if chk.status is Status.NOT_MODELED:
                    val_str = "\u2014"
                    lim_str = "\u2014"
                    margin_str = "\u2014"
                    dot = "\u26a0"
                    status_text = "NOT MODELED"
                    status_color = "#8b90a0"
                else:
                    # Format value and limit with appropriate units
                    if chk.name == "bending_stress":
                        val_str = f"{chk.actual / 1e6:.1f} MPa"
                        lim_str = f"{chk.allowable / 1e6:.1f} MPa"
                    elif chk.name == "deflection":
                        val_str = f"{chk.actual * 1e3:.2f} mm"
                        lim_str = f"{chk.allowable * 1e3:.1f} mm"
                    elif chk.name == "yield_fos":
                        val_str = f"{chk.actual:.2f}"
                        lim_str = f"{chk.allowable:.2f}"
                    elif chk.name == "euler_buckling":
                        val_str = f"FoS {chk.actual:.1f}"
                        lim_str = f"FoS {chk.allowable:.1f}"
                    else:
                        val_str = f"{chk.actual:.2f}"
                        lim_str = f"{chk.allowable:.2f}"

                    margin_str = f"{chk.margin * 100:.1f}%"

                    if chk.status is Status.PASS:
                        dot = "\u25cf"
                        status_text = "PASS"
                        status_color = "#34d399"
                    elif chk.status is Status.FAIL:
                        dot = "\u25cf"
                        status_text = "FAIL"
                        status_color = "#f87171"
                    else:  # WARNING
                        dot = "\u26a0"
                        status_text = "WARNING"
                        status_color = "#fbbf24"

                rc_class = ""
                if is_ctrl:
                    rc_class = ' class="row-safe"' if chk.status is Status.PASS else ' class="row-fail"'

                fm_html += (
                    f'<tr{rc_class}>'
                    f'{td_pre}{check_label}</td>'
                    f'{td_pre}{val_str}</td>'
                    f'{td_pre}{lim_str}</td>'
                    f'{td_n_pre}{margin_str}</td>'
                    f'{td_pre}<span style="color:{status_color};">'
                    f'{dot} {status_text}</span></td></tr>')
            fm_html += '</tbody></table>'

            # Overall status badge
            if sc.overall_status is Status.PASS:
                ov_color, ov_text = "#34d399", "ALL CHECKS PASS"
            elif sc.overall_status is Status.FAIL:
                ov_color, ov_text = "#f87171", "FAIL"
                if sc.failure_reasons:
                    ov_text += " \u2014 " + ", ".join(
                        r.replace("_", " ").title() for r in sc.failure_reasons)
            else:
                ov_color, ov_text = "#fbbf24", "WARNING"

            fm_html += (
                f'<div style="margin-top:10px;font-size:0.78rem;color:{ov_color};'
                f'font-weight:700;">{ov_text}</div>')
            fm_html += CARD_END
            st.markdown(fm_html, unsafe_allow_html=True)

            tradeoff_feedback = (
                f'<div class="rec-foot">'
                f'Picked as the <strong>{priority}</strong> option from '
                f'<strong>{n_safe}</strong> / {n_total} safe candidates. '
                f'FoS = <strong>{rec["fos"]:.2f}</strong> vs target {fos_target:.1f}. '
                f'Peak deflection <strong>{defl_str}</strong>. '
                f'Governed by <strong>{controlling.lower()}</strong>.'
                f'</div>'
            )

        # ── Stock snap comparison ────────────────────────────────────────
        if not use_stock and rec is not None:
            try:
                snap = nearest_buyable(
                    rec, float(load), float(length), str(load_case),
                    float(fos_target),
                    deflection_limit=float(deflection_limit) if deflection_limit else None,
                )
                mass_sign = "+" if snap.mass_penalty_pct >= 0 else ""
                stiff_sign = "+" if snap.stiffness_change_pct >= 0 else ""
                snap_badge = "badge-safe" if snap.snapped["safe"] else "badge-unsafe"
                st.markdown(
                    f'<div class="card" style="border-left:3px solid {ACCENT_HEX};margin-top:0.5rem;">'
                    f'<div class="rec-label">Nearest buyable stock</div>'
                    f'<div style="font-size:0.95rem;margin:0.25rem 0;">'
                    f'<b>{snap.snapped_dims_mm.get("d_mm", "?"):.0f} mm</b> '
                    f'(was {snap.original.get("dims", "?")})</div>'
                    f'<div style="display:flex;gap:1rem;font-size:0.85rem;">'
                    f'<span>Mass {mass_sign}{snap.mass_penalty_pct:.1f}%</span>'
                    f'<span>Stiffness {stiff_sign}{snap.stiffness_change_pct:.1f}%</span>'
                    f'<span>FoS {snap.snapped["fos"]:.2f} (was {snap.original["fos"]:.2f})</span>'
                    f'<span class="{snap_badge}">'
                    f'{"SAFE" if snap.snapped["safe"] else "UNSAFE"}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

        # 2. Ranked top-5 table ──────────────────────────────────────────────
        if not safe_df.empty:
            ranked = rank_candidates(df, priority)
            top5 = ranked[ranked["safe"]].head(5)
            top5_html = card(f"Top candidates &middot; {priority.title()}")
            top5_html += '<table class="mt"><thead><tr>'
            top5_html += (
                '<th>#</th><th>Material</th><th>Section &middot; Dims</th>'
                '<th class="n">FoS</th><th class="n">&sigma; MPa</th>'
                '<th class="n">&delta; mm</th><th class="n">kg</th>'
                '<th class="n">$</th><th>Controls</th><th>Why</th>'
                '</tr></thead><tbody>'
            )
            for _, trow in top5.iterrows():
                why_text = explain_winner(trow)
                if len(why_text) > 80:
                    why_text = why_text[:77] + "..."
                ctrl_label = trow["safety_case"].controlling_check.replace("_", " ").title()
                sec_label = trow["section"].replace("_", " ").title()
                top5_html += (
                    f'<tr class="row-safe">'
                    f'<td style="color:var(--muted);">{int(trow["rank"])}</td>'
                    f'<td>{mdot(trow["material"])}{trow["material"]}</td>'
                    f'<td>{sec_label} &middot; {trow["dims"]}</td>'
                    f'<td class="n">{trow["fos"]:.2f}</td>'
                    f'<td class="n">{trow["stress"]/1e6:.1f}</td>'
                    f'<td class="n">{trow["deflection"]*1e3:.2f}</td>'
                    f'<td class="n">{trow["weight"]:.4f}</td>'
                    f'<td class="n">{trow["cost"]:.2f}</td>'
                    f'<td style="font-size:0.75rem;color:var(--muted);">{ctrl_label}</td>'
                    f'<td style="font-size:0.73rem;color:var(--muted);max-width:220px;">{why_text}</td>'
                    f'</tr>'
                )
            top5_html += '</tbody></table>' + CARD_END
            st.markdown(top5_html, unsafe_allow_html=True)

        # Design Review card ─────────────────────────────────────────────────
        if rec is not None:
            review = generate_review(
                winner=rec, df=df, priority=priority,
                load=float(load), length=float(length),
                load_case=str(load_case), fos_target=float(fos_target),
                deflection_limit=float(deflection_limit) if deflection_limit else None,
            )

            # Header area
            dr_html = (
                '<div class="card">'
                '<div class="card-hd">Design Review</div>'
                f'<div style="font-size:1.2rem;font-weight:700;color:var(--text);margin-bottom:4px;">'
                f'{review.recommended}'
                f'</div>'
                f'<div style="font-size:0.84rem;color:var(--muted);line-height:1.6;margin-bottom:16px;">'
                f'{review.why_it_won}'
                f'</div>'
                '</div>'
            )
            st.markdown(dr_html, unsafe_allow_html=True)

            # Key info in 3 columns
            ki1, ki2, ki3 = st.columns(3)
            with ki1:
                margin_pct = f"{review.controlling_margin * 100:.1f}%"
                st.markdown(
                    f'<div style="background:var(--surface);border:1px solid var(--border);'
                    f'border-radius:var(--radius-sm);padding:14px 16px;">'
                    f'<div style="font-size:0.67rem;color:var(--muted);text-transform:uppercase;'
                    f'letter-spacing:0.5px;font-weight:600;">Controlling Constraint</div>'
                    f'<div style="font-size:1.05rem;font-weight:700;color:var(--text);margin-top:4px;">'
                    f'{review.controlling_constraint.replace("_", " ").title()}</div>'
                    f'<div style="font-size:0.78rem;color:var(--muted);margin-top:2px;">'
                    f'Margin: {margin_pct}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with ki2:
                st.markdown(
                    f'<div style="background:var(--surface);border:1px solid var(--border);'
                    f'border-radius:var(--radius-sm);padding:14px 16px;">'
                    f'<div style="font-size:0.67rem;color:var(--muted);text-transform:uppercase;'
                    f'letter-spacing:0.5px;font-weight:600;">Most Important Sensitivity</div>'
                    f'<div style="font-size:1.05rem;font-weight:700;color:var(--text);margin-top:4px;">'
                    f'{review.most_important_sensitivity.replace("_", " ").title()}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with ki3:
                alt_text = review.nearest_alternative if review.nearest_alternative else "None available"
                st.markdown(
                    f'<div style="background:var(--surface);border:1px solid var(--border);'
                    f'border-radius:var(--radius-sm);padding:14px 16px;">'
                    f'<div style="font-size:0.67rem;color:var(--muted);text-transform:uppercase;'
                    f'letter-spacing:0.5px;font-weight:600;">Nearest Alternative</div>'
                    f'<div style="font-size:1.05rem;font-weight:700;color:var(--text);margin-top:4px;">'
                    f'{alt_text}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Sensitivity table
            if review.sensitivities:
                sens_html = '<table class="mt"><thead><tr>'
                sens_html += '<th>Parameter</th><th class="n">+5% bumps FoS by</th><th class="n">+5% bumps &delta; by</th>'
                sens_html += '</tr></thead><tbody>'
                for s in review.sensitivities:
                    is_important = s.parameter == review.most_important_sensitivity
                    row_style = ' style="font-weight:700;background:rgba(46,100,209,0.06);"' if is_important else ''
                    td_pre = '<td style="font-weight:700;">' if is_important else '<td>'
                    td_n_pre = '<td class="n" style="font-weight:700;">' if is_important else '<td class="n">'
                    sens_html += (
                        f'<tr{row_style}>'
                        f'{td_pre}{s.parameter.replace("_", " ").title()}</td>'
                        f'{td_n_pre}{s.fos_change:+.3f}</td>'
                        f'{td_n_pre}{s.deflection_change*1e3:+.3f} mm</td>'
                        f'</tr>'
                    )
                sens_html += '</tbody></table>'
                st.markdown(sens_html, unsafe_allow_html=True)

            # Unmodeled risks
            if review.unmodeled_risks:
                risks_text = ', '.join(
                    r.replace('_', ' ').title() for r in review.unmodeled_risks
                )
                st.markdown(
                    f'<div class="callout callout-amber">'
                    f'<strong>Unmodeled risks:</strong> {risks_text}'
                    f' — these failure modes are not checked and should be verified separately.'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Recommended next step
            st.markdown(
                f'<div class="callout callout-blue">'
                f'<strong>Recommended next step:</strong> {review.recommended_next_step}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── Export buttons ───────────────────────────────────────────
            _problem = {
                "load": float(load), "length": float(length),
                "load_case": str(load_case), "fos_target": float(fos_target),
                "deflection_limit": float(deflection_limit) if deflection_limit else None,
            }
            ex1, ex2, ex3 = st.columns(3)
            with ex1:
                st.download_button(
                    "Download CSV",
                    data=export_report_bytes(df, review, _problem, priority, "csv"),
                    file_name="mechopt_candidates.csv",
                    mime="text/csv", key="dl_csv",
                )
            with ex2:
                st.download_button(
                    "Download JSON",
                    data=export_report_bytes(df, review, _problem, priority, "json"),
                    file_name="mechopt_report.json",
                    mime="application/json", key="dl_json",
                )
            with ex3:
                st.download_button(
                    "Download Report",
                    data=export_report_bytes(df, review, _problem, priority, "text"),
                    file_name="mechopt_report.txt",
                    mime="text/plain", key="dl_txt",
                )

        # 3. Why-not summary (why rejected designs failed) ───────────────────
        if n_total > n_safe:
            reasons = classify_infeasible(df)
            unsafe_reasons = reasons[df["safe"] == False]
            reason_counts = Counter()
            for r in unsafe_reasons:
                for part in r.split("|"):
                    reason_counts[part] += 1
            n_failed = n_total - n_safe
            why_html = (
                f'<div class="callout callout-amber">'
                f'<strong>Why {n_failed} design{"s" if n_failed != 1 else ""} failed:</strong>'
                f'<div style="margin-top:8px;">'
            )
            for reason, count in reason_counts.most_common():
                label = reason.replace("_", " ").title()
                why_html += (
                    f'<div style="margin:3px 0;font-size:0.82rem;">'
                    f'<span style="color:var(--red);margin-right:6px;">&#x25cf;</span>'
                    f'{label}: {count} candidate{"s" if count != 1 else ""}'
                    f'</div>'
                )
            why_html += '</div></div>'
            st.markdown(why_html, unsafe_allow_html=True)

        # 4. Tradeoff space ───────────────────────────────────────────────────
        st.markdown(
            f'<div class="card">'
            f'<div class="card-hd">Tradeoff space</div>'
            f'{tradeoff_feedback}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            tradeoff_html(df, float(fos_target),
                          float(deflection_limit) if deflection_limit else None),
            unsafe_allow_html=True,
        )
        tc1, tc2 = st.columns(2)
        with tc1:
            st.plotly_chart(
                scatter_plot(df, "weight", "fos", "Weight (kg)",
                             "Factor of Safety", float(fos_target),
                             "Weight vs FoS", rec),
                use_container_width=True, key="p_wt",
            )
        with tc2:
            st.plotly_chart(
                scatter_plot(df, "cost", "fos", "Cost ($)",
                             "Factor of Safety", float(fos_target),
                             "Cost vs FoS", rec),
                use_container_width=True, key="p_cost",
            )

        # Pareto front scatter plot ───────────────────────────────────────────
        if not safe_df.empty:
            front = pareto_front(df)
            if not front.empty:
                knee_idx = knee_point(front)
                knee_row = front.loc[knee_idx]

                fig_pareto = go.Figure()

                # Safe non-Pareto candidates: small gray dots
                non_pareto = safe_df[~safe_df.index.isin(front.index)]
                if not non_pareto.empty:
                    fig_pareto.add_trace(go.Scatter(
                        x=non_pareto["weight"], y=non_pareto["cost"],
                        mode="markers",
                        marker=dict(size=6, color="#3a3f52", opacity=0.5,
                                    line=dict(width=0.5, color="#4b5068")),
                        name="Safe (non-Pareto)",
                        text=non_pareto.apply(
                            lambda r: f"{r['material']}<br>{r['section']} {r['dims']}"
                                      f"<br>FoS {r['fos']:.2f}"
                                      f"<br>{r['weight']:.4f} kg · ${r['cost']:.2f}",
                            axis=1),
                        hoverinfo="text",
                    ))

                # Pareto front candidates: larger colored dots by material
                for mat in front["material"].unique():
                    mdf = front[front["material"] == mat]
                    fig_pareto.add_trace(go.Scatter(
                        x=mdf["weight"], y=mdf["cost"], mode="markers",
                        marker=dict(size=10, color=MAT_CLR.get(mat, "#6b7280"),
                                    line=dict(width=1, color="rgba(0,0,0,0.3)")),
                        name=mat,
                        text=mdf.apply(
                            lambda r: f"<b>{r['material']}</b><br>"
                                      f"{r['section']} {r['dims']}<br>"
                                      f"FoS <b>{r['fos']:.2f}</b><br>"
                                      f"{r['weight']:.4f} kg · ${r['cost']:.2f}",
                            axis=1),
                        hoverinfo="text",
                    ))

                # Dashed line connecting Pareto front (sorted by weight)
                front_sorted = front.sort_values("weight")
                fig_pareto.add_trace(go.Scatter(
                    x=front_sorted["weight"], y=front_sorted["cost"],
                    mode="lines",
                    line=dict(dash="dash", color=ACCENT_HEX, width=1.5),
                    name="Pareto front", showlegend=True,
                    hoverinfo="skip",
                ))

                # Knee point: ring marker
                fig_pareto.add_trace(go.Scatter(
                    x=[knee_row["weight"]], y=[knee_row["cost"]],
                    mode="markers",
                    marker=dict(size=16, color="rgba(0,0,0,0)",
                                line=dict(width=2.5, color=ACCENT_HEX),
                                symbol="circle-open"),
                    name="Knee point", showlegend=True,
                    text=[f"<b>Knee point</b><br>{knee_row['material']}<br>"
                          f"{knee_row['section']} {knee_row['dims']}<br>"
                          f"FoS {knee_row['fos']:.2f}<br>"
                          f"{knee_row['weight']:.4f} kg · ${knee_row['cost']:.2f}"],
                    hoverinfo="text",
                ))

                fig_pareto.update_layout(
                    **PLOTLY_LAYOUT,
                    title=dict(text="Pareto Front — Weight vs Cost",
                               font=dict(size=13)),
                )
                fig_pareto.update_xaxes(title_text="Weight (kg)")
                fig_pareto.update_yaxes(title_text="Cost ($)")
                st.plotly_chart(fig_pareto, use_container_width=True,
                                key="p_pareto")

        # All candidates table ────────────────────────────────────────────────
        show_all = st.checkbox("Show all candidates (including unsafe)",
                               value=False, key="b_show_all")
        view_df = df if show_all else safe_df
        label_text = (f"All candidates — {n_safe} safe / {n_total} total"
                      if show_all
                      else f"Safe candidates — {n_safe} of {n_total}")
        st.markdown(f'{card(label_text)}', unsafe_allow_html=True)
        thtml = '<table class="mt"><thead><tr>'
        thtml += ('<th>Material</th><th>Section</th><th>Dims</th>'
                  '<th class="n">FoS</th><th class="n">σ MPa</th>'
                  '<th class="n">δ mm</th><th class="n">kg</th>'
                  '<th class="n">$</th><th>Controls</th><th>Status</th>')
        thtml += '</tr></thead><tbody>'
        sorted_df = view_df.sort_values(["safe", "fos"],
                                        ascending=[False, False])
        for _, row in sorted_df.iterrows():
            rc = "row-safe" if row["safe"] else "row-fail"
            dot_c = "#34d399" if row["safe"] else "#f87171"
            thtml += (
                f'<tr class="{rc}">'
                f'<td>{mdot(row["material"])}{row["material"]}</td>'
                f'<td>{row["section"].replace("_"," ").title()}</td>'
                f'<td>{row["dims"]}</td>'
                f'<td class="n">{row["fos"]:.2f}</td>'
                f'<td class="n">{row["stress"]/1e6:.1f}</td>'
                f'<td class="n">{row["deflection"]*1e3:.2f}</td>'
                f'<td class="n">{row["weight"]:.4f}</td>'
                f'<td class="n">{row["cost"]:.2f}</td>'
                f'<td style="font-size:0.75rem;color:var(--muted);">'
                f'{row["safety_case"].controlling_check.replace("_", " ").title()}</td>'
                f'<td><span style="display:inline-block;width:8px;height:8px;'
                f'border-radius:50%;background:{dot_c};"></span></td></tr>')
        thtml += '</tbody></table>'
        st.markdown(thtml, unsafe_allow_html=True)
        st.markdown(CARD_END, unsafe_allow_html=True)

    # ── Section editor (below main layout) ───────────────────────────────────
    if rec is not None:
        with st.expander("Interactive section editor — drag handles to reshape",
                         expanded=False):
            _sec_name = rec["section"]
            _sec_mat_key = [k for k, v in MATERIALS.items()
                            if v.name == rec["material"]][0]
            _sec_mat = MATERIALS[_sec_mat_key]

            _editor_dims = {}
            if _sec_name == "rectangle":
                parts = rec["dims"].replace(" mm", "").split("x")
                _editor_dims = {"b": float(parts[0]) / 1000,
                                "h": float(parts[1]) / 1000}
            elif _sec_name == "circle":
                val = float(rec["dims"].replace("d=", "").replace(" mm", ""))
                _editor_dims = {"d": val / 1000}
            elif _sec_name == "i_beam":
                parts = rec["dims"].replace(" mm", "").split()
                outer = parts[0].split("x")
                tf_val = float(parts[1].split("=")[1].split("/")[0])
                tw_val = float(parts[1].split("=")[1].split("/")[1]
                               if "/" in parts[1] else parts[2].split("=")[1])
                _editor_dims = {"b": float(outer[0]) / 1000,
                                "h": float(outer[1]) / 1000,
                                "tf": tf_val / 1000, "tw": tw_val / 1000}
            elif _sec_name == "square_tube":
                parts = rec["dims"].replace(" mm", "").split()
                _editor_dims = {"a": float(parts[0].split("x")[0]) / 1000,
                                "w": float(parts[1].split("=")[1]) / 1000}
            elif _sec_name == "hollow_rectangle":
                parts = rec["dims"].replace(" mm", "").split()
                outer = parts[0].split("x")
                _editor_dims = {"b": float(outer[0]) / 1000,
                                "h": float(outer[1]) / 1000,
                                "w": float(parts[1].split("=")[1]) / 1000}
            elif _sec_name == "hollow_circle":
                text = rec["dims"].replace(" mm", "")
                _editor_dims = {
                    "d": float(text.split("d=")[1].split()[0].split("/")[0]) / 1000,
                    "di": float(text.split("di=")[1].split()[0]) / 1000}
            else:
                _editor_dims = {"b": 0.03, "h": 0.03}

            _editor_results = {"stress": rec["stress"],
                               "deflection": rec["deflection"],
                               "fos": rec["fos"], "safe": bool(rec["safe"])}

            if "editor_dims" not in st.session_state:
                st.session_state["editor_dims"] = None
            _active_dims = (st.session_state["editor_dims"]
                            if st.session_state["editor_dims"] else _editor_dims)

            try:
                _sfn = {
                    "rectangle": lambda d: rectangle(d["b"], d["h"]),
                    "circle": lambda d: circle(d["d"]),
                    "i_beam": lambda d: i_beam(d["b"], d["h"], d["tf"], d["tw"]),
                    "square_tube": lambda d: square_tube(d["a"], d["w"]),
                    "hollow_rectangle": lambda d: hollow_rectangle(d["b"], d["h"], d["w"]),
                    "hollow_circle": lambda d: hollow_circle(d["d"], d["di"]),
                }
                _props = _sfn.get(
                    _sec_name,
                    lambda d: rectangle(d.get("b", .03), d.get("h", .03)),
                )(_active_dims)
                _M = max_moment(float(load), float(length), str(load_case))
                _sigma = max_stress(_M, _props)
                _delta = max_deflection(float(load), float(length), _sec_mat.E,
                                        _props, str(load_case))
                _fos = factor_of_safety(_sigma, _sec_mat.sigma_y)
                _safe = _fos >= float(fos_target)
                if deflection_limit and _delta > deflection_limit:
                    _safe = False
                _editor_results = {"stress": _sigma, "deflection": _delta,
                                   "fos": _fos, "safe": _safe}
            except (ValueError, ZeroDivisionError):
                pass

            user_dims = section_editor(section=_sec_name, dims=_active_dims,
                                       results=_editor_results, key="sec_editor")
            if user_dims is not None:
                st.session_state["editor_dims"] = user_dims
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — BRACKET ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
with tab_bracket:

    br_rail, br_results = st.columns([1, 3], gap="large")

    with br_rail:
        st.markdown('<div class="rh" style="margin-top:0">Plate / Arm</div>',
                    unsafe_allow_html=True)
        br_load = st.number_input("Load P (N)", min_value=1.0, value=500.0,
                                  step=50.0, key="br_load")
        br_offset = st.number_input("Offset e (mm)", min_value=1.0,
                                    value=150.0, step=10.0,
                                    key="br_offset") / 1000.0
        br_width = st.number_input("Width (mm)", min_value=5.0, value=80.0,
                                   step=5.0, key="br_w") / 1000.0
        br_thick = st.number_input("Thickness (mm)", min_value=1.0, value=10.0,
                                   step=1.0, key="br_t") / 1000.0
        mat_opts_br = {k: v.name for k, v in MATERIALS.items()}
        br_mat_key = st.selectbox("Material", list(mat_opts_br.keys()),
                                  format_func=lambda k: mat_opts_br[k],
                                  key="br_mat")
        br_fos = st.number_input("Target FoS", min_value=1.0, value=2.0,
                                 step=0.5, key="br_fos")
        br_defl_mm = st.number_input("Max deflection (mm)", min_value=0.0,
                                     value=0.0, step=0.5,
                                     help="0 = no limit", key="br_defl")
        br_defl_limit = br_defl_mm / 1000.0 if br_defl_mm > 0 else None

        st.markdown('<div class="rh">Bolt Group</div>', unsafe_allow_html=True)
        bolt_count = st.number_input("Bolt count", min_value=1, value=4,
                                     step=1, key="br_bn")
        bolt_dia = st.number_input("Diameter (mm)", min_value=2.0, value=10.0,
                                   step=1.0, key="br_bd") / 1000.0
        bolt_spacing = st.number_input("V-spacing (mm)", min_value=5.0,
                                       value=40.0, step=5.0,
                                       key="br_bs") / 1000.0
        bolt_allow = st.number_input("Allowable stress (MPa)", min_value=50.0,
                                     value=640.0, step=50.0,
                                     key="br_ba") * 1e6
        bolt_edge = st.number_input("Edge distance (mm)", min_value=5.0,
                                    value=20.0, step=1.0,
                                    key="br_edge") / 1000.0

        st.markdown('<div class="rh">Gusset</div>', unsafe_allow_html=True)
        gusset_labels = {
            "none": "None", "flat_L": "Flat L",
            "triangular": "Triangular", "double_gusset": "Double Gusset",
            "ribbed": "Ribbed",
        }
        br_gusset_type = st.selectbox(
            "Gusset type", GUSSET_TYPES,
            format_func=lambda g: gusset_labels.get(g, g),
            key="br_gusset",
        )
        br_gusset_depth = 0.0
        if br_gusset_type != "none":
            br_gusset_depth = st.number_input(
                "Gusset depth (mm)", min_value=5.0, value=50.0,
                step=5.0, key="br_gd") / 1000.0

        st.markdown(bracket_svg(), unsafe_allow_html=True)

    br_mat = MATERIALS[br_mat_key]
    br_result = evaluate_bracket(
        P=br_load, e=br_offset, width=br_width, thickness=br_thick,
        mat=br_mat, fos_target=br_fos, bolt_count=bolt_count,
        bolt_diameter=bolt_dia, bolt_spacing_v=bolt_spacing,
        bolt_sigma_allow=bolt_allow, deflection_limit=br_defl_limit,
        gusset_type=br_gusset_type, gusset_depth=br_gusset_depth,
        edge_distance=bolt_edge,
    )

    with br_results:
        ctrl = br_result.controlling.replace("_", " ").title()
        b_cls = "badge-safe" if br_result.safe else "badge-unsafe"
        b_txt = "SAFE" if br_result.safe else "UNSAFE"
        st.markdown(
            f'{card()}'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:flex-start;margin-bottom:4px;">'
            f'<div>'
            f'<div class="rec-label">Result · controlled by {ctrl}</div>'
            f'<div style="font-size:1.1rem;font-weight:700;margin-top:4px;">'
            f'Cantilever plate + bolt group</div>'
            f'<div style="font-size:0.84rem;color:var(--muted);margin-top:2px;">'
            f'M = {br_load * br_offset:.1f} N·m · {bolt_count} bolts · '
            f'{br_mat.name}</div>'
            f'</div>'
            f'<span class="badge {b_cls}">{b_txt}</span>'
            f'</div>{CARD_END}',
            unsafe_allow_html=True,
        )

        ov1, ov2, ov3 = st.columns(3)
        ov1.metric("Overall FoS", f"{br_result.overall_fos:.2f}",
                   delta=f"{br_result.overall_fos - br_fos:+.2f} vs target")
        ov2.metric("Plate Deflection",
                   f"{br_result.plate_deflection * 1e3:.3f} mm")
        ov3.metric("Applied Moment", f"{br_load * br_offset:.1f} N·m")

        bars_html = util_bar("Plate stress",
                             br_result.plate_stress / br_mat.sigma_y
                             if br_mat.sigma_y else 0, invert=True)
        bars_html += util_bar("Bolt combined",
                              br_result.bolt.combined_utilization, invert=True)
        bearing_ratio = (br_result.bolt.bearing_stress / (1.5 * br_mat.sigma_y)
                         if br_mat.sigma_y else 0)
        bars_html += util_bar("Bearing", bearing_ratio, invert=True)
        tearout_ratio = (br_result.bolt.tearout_stress / (0.6 * br_mat.sigma_y)
                         if br_mat.sigma_y else 0)
        bars_html += util_bar("Tear-out", tearout_ratio, invert=True)
        if br_defl_limit and br_defl_limit > 0:
            bars_html += util_bar("Deflection budget",
                                  br_result.plate_deflection / br_defl_limit,
                                  invert=True)
        st.markdown(bars_html, unsafe_allow_html=True)

        dp, db = st.columns(2)
        with dp:
            st.markdown(card("Plate"), unsafe_allow_html=True)
            pp1, pp2, pp3 = st.columns(3)
            pp1.metric("Bending Stress",
                       f"{br_result.plate_stress / 1e6:.1f} MPa")
            pp2.metric("Plate FoS", f"{br_result.plate_fos:.2f}")
            pp3.metric("Tip Deflection",
                       f"{br_result.plate_deflection * 1e3:.3f} mm")
            st.markdown(CARD_END, unsafe_allow_html=True)
        with db:
            st.markdown(card("Bolt group"), unsafe_allow_html=True)
            bb1, bb2, bb3, bb4 = st.columns(4)
            bb1.metric("Shear / Bolt",
                       f"{br_result.bolt.shear_per_bolt:.1f} N")
            bb2.metric("Peak Tension",
                       f"{br_result.bolt.max_tension:.1f} N")
            bb3.metric("Bolt FoS", f"{br_result.bolt.bolt_fos:.2f}")
            bb4.metric("Utilisation",
                       f"{br_result.bolt.combined_utilization:.0%}")
            st.markdown(CARD_END, unsafe_allow_html=True)

        # Bearing & tear-out detail card
        st.markdown(card("Bearing & tear-out"), unsafe_allow_html=True)
        bt1, bt2, bt3, bt4 = st.columns(4)
        bt1.metric("Bearing Stress",
                   f"{br_result.bolt.bearing_stress / 1e6:.1f} MPa")
        bt2.metric("Bearing FoS", f"{br_result.bolt.bearing_fos:.1f}")
        bt3.metric("Tear-out Stress",
                   f"{br_result.bolt.tearout_stress / 1e6:.2f} MPa")
        bt4.metric("Tear-out FoS", f"{br_result.bolt.tearout_fos:.1f}")
        if not br_result.bolt.edge_distance_ok:
            st.markdown(
                '<div class="callout callout-amber" style="margin-top:0.3rem;">'
                'Edge distance is below 1.5d — risk of tear-out failure.</div>',
                unsafe_allow_html=True,
            )
        st.markdown(CARD_END, unsafe_allow_html=True)

        # Gusset comparison card
        if br_gusset_type != "none" and br_result.gusset is not None:
            baseline = evaluate_bracket(
                P=br_load, e=br_offset, width=br_width, thickness=br_thick,
                mat=br_mat, fos_target=br_fos, bolt_count=bolt_count,
                bolt_diameter=bolt_dia, bolt_spacing_v=bolt_spacing,
                bolt_sigma_allow=bolt_allow, deflection_limit=br_defl_limit,
                gusset_type="none", edge_distance=bolt_edge,
            )
            defl_red = ((baseline.plate_deflection - br_result.plate_deflection)
                        / baseline.plate_deflection * 100
                        if baseline.plate_deflection > 0 else 0)
            st.markdown(card("Gusset effect"), unsafe_allow_html=True)
            gc1, gc2, gc3 = st.columns(3)
            gc1.metric("Deflection reduction", f"{defl_red:.1f}%")
            gc2.metric("Added mass", f"{br_result.gusset.mass * 1000:.1f} g")
            gc3.metric("Control shifts to",
                       br_result.controlling.replace("_", " ").title())
            st.markdown(CARD_END, unsafe_allow_html=True)

        # Warnings
        if br_result.bolt.warnings:
            warn_html = '<div class="callout callout-amber" style="margin-top:0.5rem;">'
            for w in br_result.bolt.warnings:
                warn_html += f'<div style="font-size:0.85rem;">{w}</div>'
            warn_html += '</div>'
            st.markdown(warn_html, unsafe_allow_html=True)

        if br_result.controlling == "plate_bending":
            advice = ("The <strong>plate</strong> is the weak link. Stiffness "
                      "scales with thickness cubed — even a small increase in "
                      "plate thickness helps significantly. A stronger material "
                      "also works.")
        elif br_result.controlling == "bolt":
            advice = ("The <strong>bolt group</strong> governs. Try larger bolt "
                      "diameter, more bolts, or wider vertical spacing. "
                      "Changing the plate won't help.")
        elif br_result.controlling == "bearing":
            advice = ("<strong>Bearing</strong> controls. Use a thicker plate "
                      "or larger bolt diameter to spread the contact pressure.")
        elif br_result.controlling == "tearout":
            advice = ("<strong>Tear-out</strong> controls. Increase the edge "
                      "distance or use a thicker plate.")
        elif br_result.controlling == "deflection":
            advice = ("<strong>Deflection</strong> controls. Increase plate "
                      "thickness, use a stiffer material (higher E), or "
                      "shorten the load offset.")
        else:
            advice = "Design satisfies all checks."

        cls = "callout-green" if br_result.safe else "callout-amber"
        ttl = "Design is adequate" if br_result.safe else "Design does not pass"
        st.markdown(
            f'<div class="callout {cls}">'
            f'<strong>{ttl}.</strong> {advice}</div>',
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE DESIGNS
# ═════════════════════════════════════════════════════════════════════════════
with tab_compare:

    safe_beams = df[df["safe"]]

    if safe_beams.empty:
        st.markdown(
            '<div class="callout callout-amber">'
            'No safe beam designs under current inputs. Go to the '
            '<strong>Beam Optimizer</strong> tab and adjust your inputs.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(card("Beam winners by objective"), unsafe_allow_html=True)
        thtml = '<table class="mt"><thead><tr>'
        thtml += ('<th>Priority</th><th>Material</th><th>Section · Dims</th>'
                  '<th class="n">FoS</th><th class="n">σ MPa</th>'
                  '<th class="n">δ mm</th><th class="n">kg</th>'
                  '<th class="n">$</th></tr></thead><tbody>')
        prio_map = {
            "balanced": ("Balanced", "pp-bal"),
            "lightest": ("Lightest", "pp-light"),
            "cheapest": ("Cheapest", "pp-cheap"),
            "safest":   ("Safest",   "pp-safe"),
        }
        for pkey, (plbl, pcls) in prio_map.items():
            try:
                w = recommend(df, pkey)
                thtml += (
                    f'<tr><td><span class="pp {pcls}">{plbl}</span></td>'
                    f'<td>{mdot(w["material"])}{w["material"]}</td>'
                    f'<td>{w["section"].replace("_"," ").title()} · {w["dims"]}</td>'
                    f'<td class="n">{w["fos"]:.2f}</td>'
                    f'<td class="n">{w["stress"]/1e6:.1f}</td>'
                    f'<td class="n">{w["deflection"]*1e3:.2f}</td>'
                    f'<td class="n">{w["weight"]:.4f}</td>'
                    f'<td class="n">{w["cost"]:.2f}</td></tr>')
            except ValueError:
                pass
        thtml += '</tbody></table>'
        st.markdown(thtml, unsafe_allow_html=True)
        st.markdown(CARD_END, unsafe_allow_html=True)

        def top5_table(title, rows_df, metric_col, metric_label, fmt):
            h = f'<div class="card-hd">{title}</div>'
            h += '<table class="mt"><thead><tr>'
            h += (f'<th>#</th><th>Material</th><th>Dims</th>'
                  f'<th class="n">{metric_label}</th></tr></thead><tbody>')
            for rank, (_, r) in enumerate(rows_df.iterrows(), 1):
                h += (f'<tr><td style="color:var(--muted);">'
                      f'{rank}</td>'
                      f'<td>{mdot(r["material"])}{r["material"]}</td>'
                      f'<td>{r["dims"]}</td>'
                      f'<td class="n">{fmt(r[metric_col])}</td></tr>')
            return h + '</tbody></table>'

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.markdown(
                card() +
                top5_table("Lightest safe", safe_beams.nsmallest(5, "weight"),
                           "weight", "kg", lambda v: f"{v:.4f}") +
                CARD_END,
                unsafe_allow_html=True)
        with tc2:
            st.markdown(
                card() +
                top5_table("Cheapest safe", safe_beams.nsmallest(5, "cost"),
                           "cost", "$", lambda v: f"{v:.2f}") +
                CARD_END,
                unsafe_allow_html=True)
        with tc3:
            st.markdown(
                card() +
                top5_table("Strongest safe", safe_beams.nlargest(5, "fos"),
                           "fos", "FoS", lambda v: f"{v:.2f}") +
                CARD_END,
                unsafe_allow_html=True)

    st.markdown(card("Bracket summary"), unsafe_allow_html=True)
    bs1, bs2, bs3, bs4, bs5, bs6 = st.columns(6)
    bs1.metric("Overall FoS", f"{br_result.overall_fos:.2f}")
    bs2.metric("Plate Stress", f"{br_result.plate_stress / 1e6:.1f} MPa")
    bs3.metric("Bolt FoS", f"{br_result.bolt.bolt_fos:.2f}")
    bs4.metric("Bearing FoS", f"{br_result.bolt.bearing_fos:.1f}")
    bs5.metric("Controls", br_result.controlling.replace("_", " ").title())
    bc2 = "badge-safe" if br_result.safe else "badge-unsafe"
    bt2 = "SAFE" if br_result.safe else "UNSAFE"
    bs6.markdown(f'<div style="margin-top:8px;">'
                 f'<span class="badge {bc2}">{bt2}</span></div>',
                 unsafe_allow_html=True)
    st.markdown(CARD_END, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — ASSUMPTIONS
# ═════════════════════════════════════════════════════════════════════════════
with tab_assumptions:

    st.markdown(
        '<div class="callout callout-blue">'
        'MechOpt is a <strong>first-pass screening tool</strong>, not a substitute '
        'for formal engineering analysis, detailed FEA, or professional review. '
        'Verify all results with a qualified engineer before real use.'
        '</div>',
        unsafe_allow_html=True,
    )

    ca, cb = st.columns(2)

    with ca:
        st.markdown(
            card("What IS modeled") +
            '<ul class="al grn">'
            "<li>Linear-elastic material behaviour (Hooke's law)</li>"
            "<li>Static point loads only</li>"
            "<li>Small-deflection Euler–Bernoulli beam theory</li>"
            "<li>Prismatic (constant cross-section) beams</li>"
            "<li>Yielding-based factor of safety</li>"
            "<li>Simplified cantilever plate model for brackets</li>"
            "<li>Gusset variants (flat L, triangular, double, ribbed)</li>"
            "<li>Linear-elastic bolt-group load distribution</li>"
            "<li>Equal direct shear among bolts</li>"
            "<li>Moment-induced bolt tension ∝ distance from centroid</li>"
            "<li>Bolt bearing stress (AISC 1.5&sigma;<sub>y</sub>)</li>"
            "<li>Bolt tear-out / edge-distance check</li>"
            "</ul>" + CARD_END,
            unsafe_allow_html=True,
        )

    with cb:
        st.markdown(
            card("What is NOT modeled") +
            '<div class="asec">Beam</div>'
            '<ul class="al red">'
            "<li>Lateral-torsional or local buckling</li>"
            "<li>Stress concentrations at holes, notches, fillets</li>"
            "<li>Fatigue or cyclic loading</li>"
            "<li>Shear deflection (important for short, deep beams)</li>"
            "<li>Dynamic or impact loads</li>"
            "<li>Weld or joint effects</li>"
            "<li>Thermal expansion / contraction</li>"
            "<li>Combined loading (axial + bending + torsion)</li>"
            "</ul>"
            '<div class="asec">Bracket</div>'
            '<ul class="al red">'
            "<li>Weld design</li>"
            "<li>Block shear failure</li>"
            "<li>Prying action on bolts</li>"
            "<li>Plate buckling</li>"
            "<li>Bolt preload and thread engagement</li>"
            "<li>FEA-level stress distribution</li>"
            "</ul>"
            '<div class="asec">General</div>'
            '<ul class="al red">'
            "<li>Corrosion and environmental degradation</li>"
            "<li>Non-linear material behaviour (plasticity)</li>"
            "<li>Large-deflection / geometric non-linearity</li>"
            "</ul>" + CARD_END,
            unsafe_allow_html=True,
        )

    st.markdown(card("Material reference"), unsafe_allow_html=True)
    thtml = '<table class="mt"><thead><tr>'
    thtml += ('<th>Material</th><th class="n">E (GPa)</th>'
              '<th class="n">σy (MPa)</th><th class="n">ρ (kg/m³)</th>'
              '<th class="n">$/kg</th></tr></thead><tbody>')
    for _k, m in MATERIALS.items():
        thtml += (
            f'<tr><td>{mdot(m.name)}{m.name}</td>'
            f'<td class="n">{m.E/1e9:.0f}</td>'
            f'<td class="n">{m.sigma_y/1e6:.0f}</td>'
            f'<td class="n">{m.rho:.0f}</td>'
            f'<td class="n">{m.cost:.1f}</td></tr>')
    thtml += '</tbody></table>'
    st.markdown(thtml, unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.78rem;color:var(--muted);margin-top:10px;">'
        'Values are nominal room-temperature properties. Cost figures are rough '
        'order-of-magnitude — use for relative comparisons only.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(CARD_END, unsafe_allow_html=True)

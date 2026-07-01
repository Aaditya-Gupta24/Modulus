# MechOpt — UI Redesign Specification

**Target:** A custom web front-end (HTML/CSS/JS or React) that calls the existing Python
engine. **Aesthetic:** dark engineering cockpit — depth, glow, animated instruments,
data-dense but calm. **Goal:** replace the flat scroll-heavy Streamlit tabs with a real
app shell: icon-rail sidebar, organized views (no endless scroll), hover tooltips, and
purposeful motion.

_Companion to PROJECT_CONTEXT.md, IMPROVEMENT_PLAN.md. Drafted 2026-06-30._

---

## 1. Design principles

1. **Instrument, not form.** It should read like a serious analysis tool, not a web form.
   Results are the hero; inputs are a quiet control panel.
2. **Justify, compare, warn, validate** — the product thesis must be *visible*. The safety
   case, the "why it won," and the unmodeled-risk warnings are first-class UI, not footnotes.
3. **Motion with meaning.** Every animation communicates state change (a value updating, a
   constraint becoming active, a design failing). No decorative-only motion.
4. **Depth over flatness.** Layered surfaces, soft inner/outer shadow, subtle glow on live
   data. This is the antidote to "vibecoded flat."
5. **Calm density.** Lots of data, but grouped into cards/panels with generous internal
   rhythm so it never feels cramped.

---

## 2. Architecture (how the front-end talks to Python)

- **Engine stays in Python.** Expose the existing functions (`evaluate_candidates`,
  `recommend`, `rank_candidates`, `pareto_front`, `evaluate_bracket`, failure-mode + design-
  review modules) behind a thin **FastAPI** (or Flask) JSON API. The front-end is a static
  SPA that POSTs inputs and renders returned JSON.
- **Why this works:** `index.html` already proves a pure-JS front-end can drive the model.
  The redesign generalizes that into the whole app, with the Python oracle as the source of
  truth (parity rule from LOOPED_PROMPT still applies: JS display ↔ Python numbers).
- **Recommended stack:** React + TypeScript + a lightweight state store, charts via
  Plotly/ECharts/D3, motion via Framer Motion (or CSS + Web Animations API if vanilla).
  Section/bracket diagrams stay **SVG** (already the case).
- **No localStorage dependency for logic**; persist user prefs (unit system, theme density)
  only as convenience.

---

## 3. Design tokens (dark cockpit)

### Color
```
--bg-base       #0B0F17   page background (near-black blue)
--bg-panel      #131927   primary card/panel surface
--bg-panel-2    #1A2233   raised/nested surface
--bg-rail       #0E131D   sidebar rail
--stroke        #232C3D   hairline borders
--stroke-soft   #1B2233   inner dividers

--text-hi       #E8EDF7   primary text
--text-mid      #9AA4B8   secondary text
--text-low      #5E6880   tertiary / captions

--accent        #3B82F6   primary action / brand (electric blue)
--accent-glow   #3B82F6   used at low alpha for glows
--cyan          #22D3EE   data highlight / live values
--violet        #8B5CF6   secondary series

--pass          #34D399   pass / safe (green)
--warn          #FBBF24   warning / not-modeled (amber)
--fail          #F87171   fail / unsafe (red)
--neutral       #64748B   inactive
```
Status colors must be used **consistently**: green=pass, amber=warning/not-modeled,
red=fail. This is the safety-case language; never reuse those hues decoratively.

### Typography
- **Display / headings + wordmark:** a **sharp-edged, angular** technical face — NOT a soft
  or rounded font. Primary pick **Chakra Petch** (sharp corners, technical) or **Saira** /
  **Rajdhani**; cleaner alternate **Archivo**. See **Revision R1** for the landing direction.
- **UI / labels:** Inter. 600 for labels, 400 for body.
- **Numbers / data:** a tabular-figure mono — **JetBrains Mono** or **IBM Plex Mono** — for
  every engineering value (stress, FoS, margins, dimensions). Mono numerals are the single
  biggest "this is a real tool" signal. Always `font-variant-numeric: tabular-nums`.
- Scale (px): 32/24/20 headings · 15 body · 13 labels · 11 caption/overline (uppercase,
  letter-spacing 1px for section headers like the current `.rh` style).

### Spacing & shape
- 4px base grid; common gaps 8 / 12 / 16 / 24 / 32.
- Radius: 6 (controls), 10 (cards), 14 (panels), 999 (pills/chips).
- Panel padding 20–24.

### Elevation (the anti-flat layer)
```
--e1  0 1px 0 rgba(255,255,255,.03) inset, 0 1px 2px rgba(0,0,0,.4)
--e2  0 0 0 1px var(--stroke), 0 8px 24px rgba(0,0,0,.45)
--glow-live   0 0 0 1px rgba(34,211,238,.35), 0 0 18px rgba(34,211,238,.18)
--glow-accent 0 0 24px rgba(59,130,246,.25)
```
Live/updating values get `--glow-live` briefly when they change (see motion).

### Motion tokens
```
--dur-fast 120ms   hover, press
--dur-base 220ms   value updates, reveals
--dur-slow 420ms   view transitions, chart draw-in
--ease-out  cubic-bezier(.16,1,.3,1)      enters
--ease-io   cubic-bezier(.65,0,.35,1)     moves
```
Respect `prefers-reduced-motion`: drop transforms, keep opacity, kill loops.

---

## 4. App shell layout

```
┌──────┬──────────────────────────────────────────────────────────┐
│      │  TOP BAR: brand · breadcrumb/view title · unit chip ·     │
│ RAIL │  run-state · export menu                                  │
│(icon)├──────────────────────────────────────────────────────────┤
│      │                                                           │
│  ▣   │   CONTENT AREA (per-view)                                 │
│  ◧   │   left: control panel (inputs)                            │
│  ⟁   │   right/main: results instruments                         │
│  ⊞   │                                                           │
│  ⓘ   │                                                           │
│      │                                                           │
│ ⚙ ▽ │                                                           │
└──────┴──────────────────────────────────────────────────────────┘
```

### Sidebar (icon rail) — the core ask
- **Collapsed default:** 64px rail of icons only. **Expands to ~220px on hover** (label
  slides in) OR via a pin toggle at the bottom. Smooth width transition (`--dur-base`,
  `--ease-out`).
- **Tooltips:** when collapsed, hovering an icon shows a label tooltip after ~300ms — dark
  chip, arrow pointing to the icon, name + one-line description. (e.g. hover ⟁ → "Bracket
  Analysis · plate + bolt group + gusset"). This satisfies the "names on hover" requirement.
- **Active item:** left accent bar (3px, `--accent`), icon switches to `--text-hi`,
  subtle `--glow-accent` behind it.
- **Sections:** primary nav (views) top-aligned; utility (settings, theme, help) bottom-
  aligned with a divider.
- **Icon set:** use a consistent line-icon family (Lucide/Phosphor). Each view gets a
  distinct, legible glyph.

### Top bar
- Left: collapsed brand mark (hexagon) + current view title (animated swap on nav).
- Right: **unit-system chip** (SI/MM/Imperial, click to cycle or dropdown), a **run-state
  pill** ("Up to date" / "Recomputing…" with a pulsing dot), and an **Export** dropdown
  (CSV / JSON / PDF / TXT).

---

## 5. Navigation / information architecture

Replace the 4 flat tabs with **menu views**. Each view is paged/sectioned internally with
**segmented sub-tabs** (pill toggles) instead of long scroll.

| Rail icon | View | Sub-tabs (segmented, no scroll) |
|---|---|---|
| ▣ Dashboard | **Overview** (new) | — single instrument summary: last beam result, last bracket result, quick links |
| ◧ Beam | **Beam Optimizer** | `Setup` · `Results` · `Tradeoffs` · `Design Review` |
| ⟁ Bracket | **Bracket Analysis** | `Setup` · `Plate & Bolts` · `Gusset` · `Warnings` |
| ⊞ Compare | **Compare** | `By Objective` · `Materials` · `Tradeoff Space` |
| ⚗ Validate | **Validation & Case Studies** (surface existing FE validation + case studies) | `FE Validation` · `Case Studies` |
| ⓘ Assumptions | **Scope & Limits** | single scannable list, grouped |
| ⚙ Settings | **Settings** | units, theme density, motion toggle |

> The Beam advanced features (**Monte Carlo uncertainty**, **Load-Case Envelope**,
> **interactive section editor**) become panels inside `Beam ▸ Results`/`Tradeoffs` rather
> than buried expanders — promote them; they're differentiators.

---

## 6. View-by-view specification

### 6.1 Beam Optimizer
**`Setup` sub-tab — the control panel (left, ~360px) + live preview (right).**
- Grouped control cards: **Loading** (Load P, Span L, Load case selector as icon options
  for the 4 cases with little beam diagrams), **Constraints** (Target FoS, Max deflection),
  **Priority** (2×2 segmented pills: Lightest / Cheapest / Safest / Balanced),
  **Materials** (multi-chip selector, 6 materials, each chip a color-coded token),
  **Cross-sections** (6 toggle tiles showing the section glyph), **Design mode** (toggle:
  Conceptual sweep ↔ Standard stock).
- Right: a **live section + load preview** SVG that animates as inputs change (the beam
  flexes, the load arrow scales). This is a key anti-flat moment.

**`Results` sub-tab.**
- **Recommended Design hero card** — large, glowing, mono numbers; section glyph; the
  one-line "why it won."
- **Safety-Case table** (Check / Value / Limit / Margin / Status). Each row: status pill,
  and a **horizontal margin meter** (bar from 0 → fill to margin, colored by status).
  Bars **animate fill** on load/update. "Not modeled" rows render amber with a dashed bar.
- **Section editor panel** (the interactive SVG, drag handles) with live neutral-axis,
  outer-fiber, and "material far from NA is efficient" annotations.
- **Monte Carlo panel** (was an expander): a probability-of-passing gauge + histogram;
  "Run" button triggers an animated sampling sweep.

**`Tradeoffs` sub-tab.**
- **Pareto scatter** (weight vs cost vs FoS vs deflection) — points draw in staggered;
  Pareto front highlighted as a glowing line; **knee point** pulses; recommended point
  marked; safe vs unsafe styled distinctly. Hover a point → tooltip card with the design.
- **Top-5 ranked table** (Rank / Design / Why good / Controls / Risk) — the report's table.
- **Load-Case Envelope panel**: matrix of cases × checks with the governing case
  highlighted.

**`Design Review` sub-tab.** — the capstone "special feature."
- A document-style review panel: Recommended design · Why it won · Controlling constraint ·
  Most important sensitivity (with a small tornado/bar viz) · Risks (unmodeled, as amber
  chips) · Nearest practical alternative · Recommended next step. Reads like a junior
  engineer's review. Subtle typewriter/stagger reveal on first render.

### 6.2 Bracket Analysis
- `Setup`: Plate/Arm (Load, Offset e, Width, Thickness, Material), Target FoS, Max
  deflection; Bolt Group (count, diameter, V-spacing, allowable stress, edge distance);
  Gusset selector (flat L / triangular / double / ribbed) as diagram tiles.
- Hero: **animated bracket SVG** that redraws with geometry (gusset appears, bolts lay out,
  load arrow at offset). The most "emotionally interesting" element — make it the centerpiece.
- `Plate & Bolts`: cards for Plate, Bolt group, Bearing & tear-out (tear-out, block shear,
  edge distance) with margin meters + status pills.
- `Gusset`: before/after comparison ("3 mm gusset → −72% tip deflection, +18 g; control
  moves plate→bolt") with an animated delta.
- `Warnings`: wall-substrate + "does not check wall anchorage" + unmodeled effects, as
  active warning cards (amber), not buried text.

### 6.3 Compare
- `By Objective`: beam winners (lightest/cheapest/safest/balanced) as 4 instrument cards.
- `Materials`: the 6-material reference table — sortable, mono numbers, color tokens.
- `Tradeoff Space`: a shared scatter to compare saved candidates.

### 6.4 Validation & Case Studies
- Surface the existing FE validation (`validation/`, the <0.01% match) as a credibility
  panel with the validation plot. Case studies (shelf bracket, robot-arm link, mini-crane)
  as story cards.

### 6.5 Scope & Limits / Settings — straightforward grouped content.

---

## 7. Component library

- **Panel / Card:** `--bg-panel`, radius 14, `--e2`, overline header (uppercase 11px), an
  optional status accent strip on the left edge.
- **Stat / value:** mono tabular numerals, unit in `--text-low`, optional delta arrow.
- **Status pill:** pass/warn/fail/neutral; filled dot + label; consistent palette.
- **Margin meter:** horizontal bar 0→fill, color by status, animated width; negative
  margins render as a red bar growing left of a zero baseline.
- **Gauge:** radial for FoS / probability-of-passing; needle eases to value; arc colored
  by zone.
- **Data table:** sticky header, zebra at 2% white, hover row highlight, mono number
  columns right-aligned.
- **Segmented control / pills:** for sub-tabs and priority; sliding active indicator.
- **Chip selector:** materials & sections; selected = filled token + check.
- **Tooltip:** dark chip, 8px radius, arrow, 300ms delay, used on rail icons and chart points.
- **SVG diagram:** section editor, bracket, beam preview — all live/animated.
- **Toast / run-state:** non-blocking "Recomputing…" → "Up to date."

---

## 8. Animation & micro-interaction inventory

| Trigger | Animation | Token |
|---|---|---|
| View change (rail nav) | content cross-fade + 8px slide up; title swap in top bar | `--dur-slow / --ease-out` |
| Sidebar hover | rail width 64→220, labels fade/slide in | `--dur-base / --ease-out` |
| Icon hover (collapsed) | tooltip fade + 4px slide from rail | `--dur-fast`, 300ms delay |
| Value recompute | number rolls/counts to new value; brief `--glow-live` ring | `--dur-base` |
| Safety-case load | margin bars fill left→right, staggered 40ms/row | `--dur-base / --ease-out` |
| Status flip pass↔fail | pill color morph + tiny shake on new fail | `--dur-fast` |
| Pareto chart | points fade+scale in staggered; front line draws; knee pulses (loop, subtle) | `--dur-slow` |
| Section/bracket edit | SVG morphs geometry; annotations reflow | `--dur-base / --ease-io` |
| Monte Carlo run | histogram bars rise sequentially; gauge needle sweeps | `--dur-slow` |
| Design Review reveal | sections stagger-fade in top→bottom | `--dur-base` |
| Card hover | lift 2px + shadow deepen + hairline brighten | `--dur-fast` |
| Button press | scale .98 + inner shadow | `--dur-fast` |

Rules: one signature motion per view (don't animate everything at once); loops only for
the knee-point pulse and the run-state dot; everything obeys `prefers-reduced-motion`.

---

## 9. States to design

- **Empty / first load:** ghost instruments with a "Set inputs to run" prompt.
- **Recomputing:** skeleton shimmer on result panels + top-bar run-state pill.
- **All safe:** subtle green accent on the recommended card (the current `ALL SAFE` flag).
- **No safe candidate:** prominent but calm card — "No design satisfies the constraints,"
  with the why-not breakdown (failed-by-stress / deflection / buckling / invalid geometry).
- **Error:** inline panel, never a raw stack trace.

---

## 10. Responsive

- ≥1280px: full two-column (control panel + instruments).
- 900–1280: control panel collapses into a top drawer; instruments full-width.
- <900: rail becomes a bottom bar or hamburger; cards stack; charts switch to compact mode.
- Tables get horizontal scroll with a frozen first column.

---

## 11. Accessibility & performance

- Contrast: body text ≥ 4.5:1 on `--bg-panel`; don't rely on color alone for status — pair
  every status color with an icon/label.
- Full keyboard nav for rail + sub-tabs; visible focus ring (`--cyan` at 40%).
- Tooltips reachable on focus, not just hover.
- Charts: animate once, then static; debounce recompute (~150ms) so dragging the section
  editor doesn't thrash the API.

---

## 12. Handoff checklist (for whoever builds it)

1. Stand up the FastAPI layer exposing the engine functions as JSON endpoints.
2. Build the shell first: rail + tooltips + top bar + view router + tokens.
3. Port views in order: Beam (Setup→Results→Tradeoffs→Review) → Bracket → Compare →
   Validation → Scope/Settings.
4. Wire the SVG diagrams (reuse existing section/bracket SVG logic).
5. Enforce the parity rule: every displayed number must match the Python oracle
   (PROJECT_CONTEXT §7) — keep that as a test.
6. Pass: dark-cockpit tokens applied, every rail icon has a hover tooltip, no view requires
   long scroll (sub-tabs instead), and each view has its one signature animation.

---

## 13. Revision R1 — Landing / Dashboard direction (supersedes §4 hero & §6 dashboard)

_Added 2026-06-30 after first build review. Reference site the user wants to emulate:_
**https://9mothers.com/** — a dark, immersive, full-bleed landing with sharp bold type,
bracketed monospace overline tags (`[ MECHANICAL DESIGN OPTIMIZATION ]`), generous negative
space, technical-readout stat blocks, and a **scroll-driven sectioned narrative**. NOT panels
crammed into the middle of the viewport. This R1 governs the Dashboard/landing only; the
analysis views keep the dark-cockpit spec above.

### R1.1 Overall feel
- Full-viewport immersive hero, then content revealed **on scroll** as full-width section
  bands — each introduced by a bracketed mono overline tag, like 9mothers.
- Restrained and monochrome **except** the MechOpt wordmark, which is the single **dynamic**
  focal point (animated within the brand palette — see R1.3). Everything else: sharp,
  technical, high-contrast, lots of space.

### R1.2 Typography — SHARP-EDGED (replaces the soft/rounded look)
- Switch the display/heading + wordmark font to a **sharp, angular** technical face.
  Primary: **Chakra Petch** (sharp corners, engineering feel). Alternates: **Saira**,
  **Rajdhani**, or cleaner **Archivo**. Do **not** use rounded/soft fonts.
- Headlines: large, bold, tight letter-spacing. Body stays Inter; data stays mono.
- The current text reads generic — this is the fix for "vibecoded" type.

### R1.3 MechOpt wordmark — DYNAMIC (animated, NOT rainbow)
- The wordmark must feel **dynamic**, not static — but **no rainbow**. Keep it in the brand
  palette (electric blue / cyan / violet from the tokens), not a full spectrum.
- Treatment options (pick one): a slow **gradient shimmer/flow** within the brand palette
  across the letters (`background-clip:text` + animated gradient position); OR a subtle
  **reactive** effect where the wordmark responds to the cursor / the heatmap background
  (e.g. accent glow tracks the pointer); plus a one-shot reveal on mount.
- Disable any loop under `prefers-reduced-motion` (static brand-gradient fallback).

### R1.4 Reactive heatmap-grid background (replaces the static background)
- Replace the static hero background with an **interactive, cursor-reactive heatmap on a
  technical grid** — thematically an FEA stress-field contour (on-brand for a structural
  tool).
- Behavior: a faint grid; a heat/contour field that **warps and glows toward the cursor**
  (like probing a stress field); slow ambient motion when idle.
- Implementation: WebGL shader (preferred) or canvas; FPS-capped, paused when off-screen,
  **disabled under `prefers-reduced-motion`** with a static subtle-grid fallback. Keep it
  low-alpha so foreground text stays fully legible.

### R1.5 Remove the beam diagram from the hero
- Delete the static beam/load SVG diagram currently in the hero.

### R1.6 Remove the 3 center blocks from the middle of the screen
- The **Engine/Capabilities**, **Library/Materials**, and **System/Status** panels must NOT
  float as three boxes in the middle of the hero.
- Move them **out of the hero** into scroll-down section bands below the fold (each a
  full-width band with a bracketed overline + technical-readout styling), in the 9mothers
  sectioned-narrative style. The hero contains only: bracketed tag + rainbow wordmark +
  one-line description + reactive background.

### R1.7 Fix the description-line alignment bug
- The hero subtitle's animated rotating word (lightest / cheapest / safest) is breaking out
  of the baseline and overlapping ("...the [safest] design"). Fix the inline alignment:
  fixed-width inline container, baseline-aligned swap — or drop the word-swap animation and
  use static copy. **No words floating out of line.**

### R1.8 Revised dashboard layout order
1. **Hero (full viewport):** bracketed mono tag → rainbow animated wordmark → one-line
   description (aligned) → reactive heatmap-grid background. Nothing else.
2. **Scroll ↓** indicator (like 9mothers).
3. **Section bands** (full-width, bracketed overline each): Capabilities → Materials Library
   → System Status → Quick actions. Quick actions live near the **end**, after scroll
   (carries the earlier note: quick-start belongs below the fold and must actually navigate).
4. Unit-system chip + Export stay **hidden on the dashboard** (only on analysis views).

### R1.9 Build notes
- Heatmap shader: keep it a self-contained component; expose intensity/grid-density props.
- Verify at localhost:5173; check reduced-motion path; screenshot hero + one scrolled band.
- Parity rule still holds for any numbers shown (Materials table values = engine values).

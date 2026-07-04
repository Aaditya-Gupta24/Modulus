# MechOpt Visual UI Reference and Improvement Plan

**Project:** MechOpt  
**Purpose:** Website/UI reference guide for making MechOpt more visual, more impressive, and easier to understand.  
**Main goal:** Make MechOpt feel like a visual engineering design cockpit, not a basic calculator or form-heavy Streamlit app.  
**Best reference mix:** SkyCiv for beam workflow, Calcs.com for engineering calculation transparency, SimScale for CAE polish, Onshape for CAD-like interaction, and Mobbin for general dashboard/product UI patterns.

---

## 1. Current MechOpt baseline

MechOpt is already a strong mechanical engineering portfolio project. It is a Python-based mechanical design optimization tool that evaluates beams and wall-mounted brackets by stress, deflection, factor of safety, weight, and cost. It sweeps many candidate designs across materials, sections, and dimensions, then recommends the best design based on a selected priority.

Current app structure:

- **Beam Optimizer**
  - Inputs: load, span, load case, target FoS, deflection limit, material selection, section selection, optimization priority.
  - Outputs: recommended design card, candidate table, weight/FoS plot, cost/FoS plot.

- **Bracket Analysis**
  - Inputs: load, offset, plate width, plate thickness, material, target FoS, deflection limit, bolt count, bolt diameter, bolt spacing, bolt allowable.
  - Outputs: plate result, bolt result, controlling constraint, safe/unsafe result.

- **Compare Designs**
  - Side-by-side view of top safe beam candidates.

- **Assumptions & Limitations**
  - Documentation of equations and modeling limits.

- **Existing visual component**
  - A bidirectional Streamlit custom component with an SVG section editor where editing dimensions sends values back to Python and recomputes stress/FoS.

- **Validation strength**
  - Independent 1D finite-element validation exists.
  - Analytical model matches FE very closely for the implemented beam assumptions.
  - Case study shows an I-beam can be dramatically lighter than a solid section at equal FoS.

This means the UI redesign should not hide the engineering. The best direction is to make the engineering more visible.

---

## 2. Product positioning

### One-line positioning

> **MechOpt is a visual mechanical design screener that helps users choose lighter, cheaper, and safer beams and brackets using transparent engineering calculations.**

### What the UI should communicate in 5 seconds

A visitor should instantly understand:

1. What structure is being analyzed.
2. What load case is applied.
3. Which design wins.
4. Why it wins.
5. Whether it is safe.
6. What tradeoff was made: weight, cost, strength, deflection, or buckling.
7. How the calculation was validated.

### The desired user feeling

The app should feel like:

- A compact engineering cockpit.
- A structural calculator with visual feedback.
- A lightweight simulation dashboard.
- A portfolio-quality ME project.
- A tool made by someone who understands engineering tradeoffs, not just frontend styling.

It should not feel like:

- A spreadsheet pasted into a web app.
- A generic Streamlit demo.
- A black-box optimizer.
- A toy calculator with unexplained numbers.

---

## 3. Reference site breakdown

## 3.1 SkyCiv Beam Calculator

**Reference role:** Best direct reference for the beam optimizer workflow.

SkyCiv is the closest reference because it already works around the same mental model: beam length, supports, sections, materials, loads, solving, and result diagrams. It includes reactions, shear force diagrams, bending moment diagrams, deflection, stress, section properties, reports, hand calculations, and optimization-related features.

### What SkyCiv does well

- Beam setup is visual and engineering-specific.
- The workflow follows the natural structural analysis order:
  1. Define beam.
  2. Add supports.
  3. Add section/material.
  4. Add loads.
  5. Solve.
  6. View diagrams/results.
- It shows multiple engineering outputs, not just one number.
- It has professional trust signals: reports, hand calculations, design-code language, section builder, 3D render.

### Weaknesses/opportunities for MechOpt

SkyCiv is powerful, but it is broad and structural-engineering oriented. That creates opportunities for MechOpt:

- SkyCiv can feel complex for a student or portfolio reviewer.
- It is analysis-first; MechOpt should be **optimization-first**.
- SkyCiv shows results, but MechOpt can better explain **why one design beats another**.
- SkyCiv focuses on structural tools generally; MechOpt can focus on mechanical design tradeoffs: weight, cost, factor of safety, manufacturability, section efficiency.
- SkyCiv has many features; MechOpt can win through clarity and speed.

### How MechOpt can improve on SkyCiv

Build a beam interface that is simpler but more explanatory:

- Show a **live beam diagram** before the user presses optimize.
- Show force arrows, support icons, span dimensions, and section preview.
- Show **deflected shape overlay** after solving.
- Show simplified shear, moment, and deflection diagrams in stacked cards.
- Make the winning candidate the hero output, not buried in a table.
- Add a **why this won** explanation:
  - “This I-beam wins because it places material farther from the neutral axis, increasing I without adding much mass.”
- Add **before/after comparison**:
  - Baseline solid rectangle vs optimized I-beam.
- Add **Pareto front view**:
  - Highlight designs that are not dominated in weight/cost/FoS.
- Add **section efficiency visualization**:
  - Show area, moment of inertia, and I/A ratio visually.

### What to borrow from SkyCiv

- Beam diagram canvas.
- Support and load icons.
- Result diagram stack.
- Section properties panel.
- Report/export mindset.
- Solve/result workflow.

### What not to copy

- Too many menus.
- Too much structural-code complexity.
- Dense professional engineering UI that may overwhelm a student portfolio viewer.

---

## 3.2 Calcs.com / ClearCalcs

**Reference role:** Best reference for transparent engineering calculations and reports.

Calcs.com is useful because it makes engineering calculations feel traceable. It emphasizes prebuilt structural calculators, formula references, conditional checks, design standards, standard/detailed modes, and calculation reports.

### What Calcs.com does well

- Strong calculation trust.
- Clear engineering workflow.
- Formula references and step-by-step checks.
- Standard mode vs detailed mode.
- Report/export mindset.
- Good for proving that the app is not a black box.

### Weaknesses/opportunities for MechOpt

Calcs.com is strong on calculation clarity, but it can be text/report heavy.

MechOpt can improve by making the calculation visual:

- Instead of only showing equations, connect equations to diagrams.
- When showing `sigma = M*c/I`, visually highlight:
  - `M` on the bending moment diagram.
  - `c` on the cross-section.
  - `I` as the section stiffness property.
- When showing bracket bolt checks, highlight:
  - Direct shear on all bolts.
  - Moment-induced tension distribution.
  - The most loaded bolt.
- Use collapsible detailed calculations so casual visitors are not overwhelmed.

### How MechOpt can improve on Calcs.com

Add a **visual calculation drawer**:

```text
Result card
  Safe: Yes
  FoS: 2.41
  Controlling check: Deflection

[Show calculation path]
  1. Max moment: M = P*L
  2. Stress: sigma = M*c/I
  3. Deflection: delta = P*L^3/(3EI)
  4. FoS: sigma_y/sigma
  5. Pass/fail check
```

For each line, include a tiny diagram or highlighted label:

- Load arrow for `P`.
- Span dimension for `L`.
- Neutral axis/c label for `c`.
- Cross-section stiffness label for `I`.
- Yield strength badge for material.

### What to borrow from Calcs.com

- Detailed calculation mode.
- Formula references.
- Pass/fail checks.
- Report generation idea.
- “Never be in the dark” style of transparency.

### What not to copy

- Too much document-like UI above the actual visual result.
- Too many code/design-standard elements for this project stage.

---

## 3.3 SimScale

**Reference role:** Best reference for professional CAE/simulation visual polish.

SimScale is more advanced than MechOpt because it is a cloud simulation platform. But it is valuable as a visual style reference: setup panels, simulation categories, professional result pages, cloud engineering language, and physics-based dashboard polish.

### What SimScale does well

- It looks like serious engineering software.
- It separates setup, solve, and post-processing.
- It makes simulation feel visual and high-value.
- It uses professional language around validation, FEA, physics, and optimization.
- It has a modern web-app feel instead of an old calculator feel.

### Weaknesses/opportunities for MechOpt

SimScale-style tools can feel heavy:

- Many users associate FEA with meshing, solver settings, and setup complexity.
- It may take time before a user gets a result.
- It can feel intimidating for beginners.

MechOpt can win by being:

- Instant.
- Lightweight.
- Educational.
- Transparent.
- Easier to demo in 30 seconds.

### How MechOpt can improve on SimScale

Use CAE-style visuals without CAE-style complexity:

- Add a **simulation-lite** visual layer:
  - Deflected shape overlay.
  - Stress color gradient.
  - Safe/unsafe badges.
  - Critical section marker.
  - Critical bolt marker.
- Show validation as a trust card:
  - “Analytical model validated against independent FE solver.”
  - “FE agreement: < 1e-4% for implemented beam cases.”
- Add a validation tab or panel with:
  - Analytical vs FE plot.
  - Error card.
  - Euler-Bernoulli vs Timoshenko note.
- Avoid making the user define mesh, material models, contacts, or boundary conditions beyond the project’s scope.

### What to borrow from SimScale

- Professional engineering dashboard style.
- Result visualization hierarchy.
- Physics categories.
- Validation/trust language.
- Cloud simulation polish.

### What not to copy

- Heavy solver workflows.
- Meshing UI.
- Advanced FEA settings that are not supported by MechOpt.

---

## 3.4 Onshape

**Reference role:** Best reference for CAD-like interaction and engineering workspace layout.

Onshape is a cloud CAD platform. MechOpt should not try to become CAD software, but it can borrow the interaction style: object tree, visual canvas, property panels, dimensions, version/compare thinking, and a central workspace.

### What Onshape does well

- Central model canvas.
- Left-side feature/design tree.
- Right-side property panels.
- Versioning, branching, and comparison mindset.
- Cloud-native engineering collaboration feel.
- CAD-like confidence.

### Weaknesses/opportunities for MechOpt

Onshape is design-first, not optimization-first.

MechOpt can win by answering questions CAD does not answer immediately:

- Which design is lightest and safe?
- Which design is cheapest and safe?
- Which design fails first and why?
- How much mass do I save by using a hollow section or I-beam?
- What is the controlling constraint?

### How MechOpt can improve on Onshape

Borrow the CAD layout, but keep the scope focused:

```text
Left: Inputs / design tree
Center: Beam or bracket visual canvas
Right: Results / recommendation / checks
Bottom: Candidate table + tradeoff plots
```

Add a **design tree** concept:

```text
Design setup
├─ Structure: Beam
├─ Load case: Cantilever end load
├─ Material set: Steel, Aluminum, Titanium
├─ Sections: Rectangle, Circle, I-beam, Hollow rectangle
├─ Constraints: FoS >= 2.0, deflection <= 5 mm
└─ Optimization priority: Balanced
```

This makes the app feel more like engineering software and less like scattered widgets.

### What to borrow from Onshape

- CAD-like workspace layout.
- Feature tree mental model.
- Interactive dimensions.
- Visual canvas first.
- Compare/design alternatives concept.

### What not to copy

- Full CAD modeling complexity.
- Deep part/assembly workflows.
- Feature history mechanics.

---

## 3.5 Mobbin

**Reference role:** Best reference for general web-app patterns, not engineering-specific UI.

Mobbin is useful for studying polished dashboards, onboarding flows, filters, cards, tables, settings, and empty states. It should be used for UI polish, not for engineering logic.

### What Mobbin does well

- Real-world UI patterns.
- Modern dashboard inspiration.
- Cards, filters, onboarding, search, settings, and flow examples.
- Helps avoid random Dribbble-style designs that do not work in real apps.

### Weaknesses/opportunities for MechOpt

Mobbin is not an engineering reference. It will not teach structural analysis UI.

MechOpt should use Mobbin for:

- Layout polish.
- Button hierarchy.
- Result cards.
- Empty states.
- Stepper flows.
- Data table design.
- Filter chips.
- Side panels.

But the engineering visualization should come from SkyCiv, SimScale, and Onshape.

### How MechOpt can improve using Mobbin patterns

Use modern SaaS patterns:

- Stepper onboarding:
  - Structure -> Load -> Material -> Constraints -> Optimize.
- Result cards:
  - Best design, FoS, weight, cost, deflection, controlling check.
- Filter chips:
  - Safe only, material, section, lightest, cheapest, highest FoS.
- Empty states:
  - “No safe design found. Try increasing section size, changing material, or relaxing deflection limit.”
- Comparison cards:
  - Top 3 safe candidates.
- Progress/status indicators:
  - “2,400 candidates evaluated.”

---

## 4. Best overall UI direction

### Recommended design theme

**Theme name:** Technical visual cockpit

### Core layout principle

Put visuals above tables.

Bad order:

```text
Inputs -> giant table -> small plot -> recommendation
```

Better order:

```text
Inputs -> live diagram -> recommendation -> tradeoff plots -> detailed table
```

### Main app layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ MechOpt                                                                      │
│ Visual beam and bracket optimization by FoS, weight, cost, and deflection     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Beam Optimizer | Bracket Analysis | Compare Designs | Validation | Docs       │
├───────────────────┬──────────────────────────────────┬───────────────────────┤
│ Setup Panel        │ Visual Engineering Canvas         │ Result Panel          │
│                   │                                  │                       │
│ Structure          │ Beam/bracket diagram              │ Best design           │
│ Load case          │ Loads/supports/dimensions         │ FoS                   │
│ Material set       │ Deflected shape/stress overlay    │ Weight                │
│ Section set        │ Section preview                   │ Cost                  │
│ Constraints        │                                  │ Deflection            │
│ Optimize button    │                                  │ Controlling check     │
├───────────────────┴──────────────────────────────────┴───────────────────────┤
│ Tradeoff plots: Pareto, Weight vs FoS, Cost vs FoS, Deflection vs Weight       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Candidate table + calculation drawer + export/report controls                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Mobile/tablet layout

For smaller screens:

```text
1. Result card
2. Visual diagram
3. Key inputs
4. Tradeoff plot
5. Candidate cards
6. Detailed table
```

---

## 5. Visual features to add

## 5.1 Beam Optimizer visual upgrades

### A. Live beam diagram

Show the beam before optimization.

Elements:

- Beam line or rectangular beam.
- Support icons:
  - Fixed wall for cantilever.
  - Pin/roller supports for simply supported beam.
- Load arrow:
  - End point load for cantilever.
  - Center point load for simply supported beam.
- Span dimension line.
- Load label.
- Material label.
- Section thumbnail.

Example wireframe:

```text
Cantilever end load

Wall
████│══════════════════════════════↓ P = 500 N
    │<----------- L = 1.20 m ----->│

Section: I-beam      Material: Aluminum 6061
Target FoS: 2.0      Deflection limit: 5 mm
```

### B. Deflected shape overlay

After solving, overlay a smooth deflected curve.

```text
Before:  ─────────────────────
After:   ───────╲____________
```

Display:

- Max deflection value.
- Deflection limit.
- Pass/fail badge.
- Exaggeration factor: “shape exaggerated 25x.”

### C. Stress color strip

Add a simplified stress visualization along the beam:

```text
Low stress ─────────────── High stress
[green] [green] [yellow] [orange] [red]
```

For a cantilever end load, peak stress should visually appear near the wall. For a simply supported center load, peak moment/stress should appear near midspan.

### D. Section efficiency preview

For each section card, show:

- Shape thumbnail.
- Area.
- Moment of inertia.
- `I/A` efficiency.
- Approx weight per meter.

Example:

```text
┌─────────────────────────────┐
│ I-Beam                      │
│     █████                   │
│       █                     │
│     █████                   │
│ I = 1.99e-6 m^4             │
│ A = 1.30e-3 m^2             │
│ Efficiency: High            │
└─────────────────────────────┘
```

### E. Winning design hero card

The recommendation should be visually dominant.

```text
┌──────────────────────────────────────────┐
│ Recommended Design                       │
│ I-beam, Steel A36, h=100 mm              │
│                                          │
│ Safe                                     │
│ FoS: 2.63    Deflection: 2.1 mm          │
│ Weight: 4.2 kg    Cost: $8.40            │
│                                          │
│ Why it won:                              │
│ Best balanced score among safe designs.  │
└──────────────────────────────────────────┘
```

### F. Pareto front plot

Current plots are useful, but the most portfolio-impressive plot is a Pareto view.

Plot idea:

- X-axis: weight.
- Y-axis: cost.
- Bubble size: FoS.
- Color/state: safe vs unsafe.
- Highlight: recommended design.
- Outline: Pareto-optimal candidates.

This immediately communicates engineering tradeoffs.

### G. “Why this design wins” explanation

This should be auto-generated from the chosen priority.

Examples:

- **Lightest priority:**
  - “This design is the lightest candidate that still passes FoS and deflection constraints.”
- **Cheapest priority:**
  - “This design minimizes estimated material cost while remaining safe.”
- **Safest priority:**
  - “This design has the highest factor of safety among all candidates.”
- **Balanced priority:**
  - “This design minimizes the combined normalized weight and cost score among safe candidates.”

Add engineering explanation:

- “Hollow and I-shaped sections often perform better in bending because they place material farther from the neutral axis, increasing moment of inertia without proportional weight increase.”

---

## 5.2 Bracket Analysis visual upgrades

The bracket tab is the biggest visual opportunity because users can instantly understand a wall bracket if it is drawn well.

### A. Bracket diagram

Show a side view:

```text
Wall
████│─────────────── bracket arm
████│               ↓ P
████│<--- e ------->│
████│
```

Show a front plate/bolt group view:

```text
Front plate
┌──────────────┐
│   ○      ○   │
│              │
│   ○      ○   │
└──────────────┘

Worst bolt highlighted
```

### B. Bolt load visualization

Show each bolt with a small vertical bar or ring thickness representing load intensity.

```text
Bolt group load share

○ small load      ● highest load
○ small load      ● highest load
```

For a moment-loaded bracket, the farthest bolt from the neutral/centroid line often becomes critical. The UI should visually mark the worst bolt.

### C. Failure mode cards

Use three cards:

```text
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Plate bending       │ │ Bolt combined load  │ │ Deflection          │
│ FoS: 2.13           │ │ FoS: 3.80           │ │ 1.8 / 5.0 mm        │
│ PASS                │ │ PASS                │ │ PASS                │
└────────────────────┘ └────────────────────┘ └────────────────────┘
```

The controlling card should be visually emphasized.

### D. Offset moment explanation

Make `M = P*e` visual:

```text
P = 500 N
      ↓
Wall ┃────────────
     ┃<-- e -->

Moment at wall = P * e
```

### E. Thickness sensitivity slider

Add a small plot or sparkline showing what happens as plate thickness increases:

- X-axis: thickness.
- Y-axis: FoS or max stress.
- Mark current thickness.
- Mark target FoS threshold.

This makes the bracket tab feel like optimization, not just checking.

### F. Bracket improvement suggestions

When unsafe, do not just say unsafe. Provide engineering actions:

```text
No safe result.
Most effective fixes:
1. Increase plate thickness.
2. Reduce load offset.
3. Increase bolt spacing.
4. Increase bolt diameter.
5. Switch to stronger material.
```

Tie suggestions to controlling constraint:

- If plate bending controls: increase thickness, width, or material yield strength.
- If bolt controls: increase bolt diameter, bolt count, spacing, or allowable strength.
- If deflection controls: increase thickness/stiffness or reduce offset.

---

## 5.3 Compare Designs visual upgrades

The compare tab should feel like a decision board.

### Current likely issue

A side-by-side table can be useful, but it does not feel visual enough.

### Better layout

Use comparison cards:

```text
┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Lightest Safe       │ │ Cheapest Safe       │ │ Safest              │
│ Aluminum I-beam     │ │ Steel rectangle     │ │ Steel I-beam         │
│ FoS: 2.05           │ │ FoS: 2.31           │ │ FoS: 5.80            │
│ Weight: 1.2 kg      │ │ Weight: 3.9 kg      │ │ Weight: 5.4 kg       │
│ Cost: $6.80         │ │ Cost: $4.20         │ │ Cost: $9.30          │
│ Defl: 4.7 mm        │ │ Defl: 3.1 mm        │ │ Defl: 1.4 mm         │
└────────────────────┘ └────────────────────┘ └────────────────────┘
```

### Add radar chart or normalized bar comparison

For each candidate, show normalized:

- Weight.
- Cost.
- FoS.
- Deflection margin.
- Stress margin.

Do not overuse radar charts, but one normalized comparison chart can be visually effective.

### Add “tradeoff sentence”

Example:

> The lightest design saves 42% mass compared with the safest design but has 64% lower safety margin.

This turns data into engineering judgment.

---

## 5.4 Validation page visual upgrades

This is a major portfolio differentiator. Do not hide it in documentation.

### Recommended tab name

Rename or add:

- **Validation & Trust**

### Add validation hero card

```text
Analytical model validated against independent FE solver
Agreement: < 1e-4% for implemented beam cases
Shear deformation note: < 0.4% error for slender beams L/h >= 15
```

### Add validation visuals

- Analytical vs FE deflection line plot.
- Error percentage bar.
- Slenderness ratio note.
- Euler-Bernoulli vs Timoshenko comparison.

### Add “model assumptions” as visual badges

```text
Implemented
[Linear elastic] [Small deflection] [Single-axis bending] [Point loads]

Not implemented yet
[Torsion] [Plasticity] [Weak-axis bending] [Asymmetric sections] [Connections beyond simplified bolt group]
```

This increases trust because you are honest about limitations.

---

## 6. Concrete visual components to build

## 6.1 `visuals/beam_svg.py`

Purpose: Generate an SVG beam diagram from load case, span, load, material, section, and result.

Functions:

```python
def render_beam_svg(
    load_case: str,
    length_m: float,
    load_n: float,
    section_name: str,
    material_name: str,
    max_deflection_m: float | None = None,
    stress_ratio: float | None = None,
) -> str:
    ...
```

Features:

- Fixed support for cantilever.
- Pin/roller supports for simply supported.
- Load arrow.
- Length dimension.
- Section/material label.
- Optional deflected shape.
- Optional stress color band.

Display with:

```python
import streamlit.components.v1 as components
components.html(render_beam_svg(...), height=280)
```

---

## 6.2 `visuals/bracket_svg.py`

Purpose: Draw wall-mounted bracket with force arrow, offset, plate, and bolt group.

Functions:

```python
def render_bracket_svg(
    load_n: float,
    offset_m: float,
    plate_width_m: float,
    plate_thickness_m: float,
    bolt_count: int,
    bolt_spacing_m: float,
    controlling_constraint: str | None = None,
    worst_bolt_index: int | None = None,
) -> str:
    ...
```

Features:

- Side view of wall and bracket.
- Front view of bolt group.
- Offset dimension arrow.
- Load arrow.
- Worst bolt highlight.
- Controlling constraint label.

---

## 6.3 `visuals/section_cards.py`

Purpose: Replace boring multiselect section names with visual cards.

Each section card should show:

- Shape thumbnail.
- Dimensions.
- Area.
- Moment of inertia.
- Relative weight.
- Relative bending efficiency.

Possible card states:

- Selected.
- Available.
- Invalid geometry.
- Recommended.

---

## 6.4 `visuals/result_cards.py`

Purpose: Reusable metric cards for both beam and bracket.

Card types:

- Safe/unsafe status.
- FoS.
- Stress.
- Deflection.
- Weight.
- Cost.
- Controlling constraint.
- Candidate count.
- Validation error.

---

## 6.5 `visuals/pareto.py`

Purpose: Create a stronger visual tradeoff plot.

Function:

```python
def plot_pareto_candidates(df, recommended_row=None):
    ...
```

Plot design:

- X-axis: weight.
- Y-axis: cost.
- Bubble size: FoS.
- Symbol or opacity: safe vs unsafe.
- Highlight recommended row.
- Optional Pareto-front outline.

---

## 6.6 `visuals/calculation_drawer.py`

Purpose: Show transparent calculations without overwhelming the user.

Use Streamlit expanders:

```python
with st.expander("Show calculation path"):
    st.latex(r"M = P L")
    st.latex(r"\sigma = \frac{M c}{I}")
    st.latex(r"FoS = \frac{\sigma_y}{\sigma}")
```

Improve it visually by adding:

- Formula.
- Substituted values.
- Result.
- Pass/fail badge.
- Tiny diagram or label.

---

## 7. Recommended information architecture

### Top navigation

```text
MechOpt
Beam Optimizer | Bracket Analysis | Compare Designs | Validation | Docs
```

### Optional landing section inside app

```text
Optimize beams and brackets visually.
Screen thousands of candidate designs by factor of safety, weight, cost, and deflection.
Validated against an independent finite-element solver.
```

CTA buttons:

- Start with beam optimizer.
- Analyze a bracket.
- View validation.

### App tabs

Recommended tabs:

1. **Beam Optimizer**
2. **Bracket Analysis**
3. **Compare Designs**
4. **Validation & Trust**
5. **Assumptions**

Separate validation from assumptions. Validation is a strength; assumptions are a boundary. Both matter, but they should not be buried together.

---

## 8. Beam Optimizer detailed layout

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Beam Optimizer                                                       │
│ Find the lightest, cheapest, safest, or balanced beam design.         │
├───────────────────────┬───────────────────────────┬─────────────────┤
│ 1. Setup               │ 2. Visual model            │ 3. Recommendation│
│ Load case              │ Beam diagram               │ Best design      │
│ Span                   │ Support/load symbols       │ FoS              │
│ Load                   │ Section preview            │ Weight           │
│ Material set           │ Deflected shape            │ Cost             │
│ Section set            │ Stress band                │ Deflection       │
│ Constraints            │                           │ Why it won       │
├───────────────────────┴───────────────────────────┴─────────────────┤
│ 4. Tradeoff dashboard                                                │
│ Pareto plot | Weight vs FoS | Cost vs FoS | Deflection vs Weight       │
├─────────────────────────────────────────────────────────────────────┤
│ 5. Candidates                                                        │
│ Filter chips | Top candidates | Full table                            │
├─────────────────────────────────────────────────────────────────────┤
│ 6. Calculation path                                                  │
│ Expandable equations, assumptions, and validation notes               │
└─────────────────────────────────────────────────────────────────────┘
```

### Beam input hierarchy

Group inputs into sections:

1. **Load case**
   - Cantilever end load.
   - Simply supported center load.
2. **Geometry**
   - Length/span.
3. **Load**
   - Force.
4. **Materials and sections**
   - Multi-select, but supported by visual cards.
5. **Constraints**
   - Target FoS.
   - Max deflection.
6. **Optimization goal**
   - Lightest.
   - Cheapest.
   - Safest.
   - Balanced.

### Beam result hierarchy

Show results in this order:

1. Safety status.
2. Recommended design.
3. FoS.
4. Deflection vs limit.
5. Weight/cost.
6. Stress.
7. Why it won.
8. Alternatives.
9. Full candidate table.

---

## 9. Bracket Analysis detailed layout

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Bracket Analysis                                                     │
│ Check plate bending, bolt group loading, deflection, and safety.      │
├───────────────────────┬───────────────────────────┬─────────────────┤
│ Setup                  │ Visual bracket model       │ Result summary   │
│ Load P                 │ Side view                  │ Safe/unsafe      │
│ Offset e               │ Front bolt view            │ Overall FoS      │
│ Plate dimensions       │ Worst bolt marker          │ Controlling mode │
│ Material               │ Moment arm annotation      │ Fix suggestions  │
│ Bolt count/spacing     │                           │                 │
├───────────────────────┴───────────────────────────┴─────────────────┤
│ Failure mode cards: Plate bending | Bolt group | Deflection           │
├─────────────────────────────────────────────────────────────────────┤
│ Sensitivity: thickness, bolt spacing, offset, bolt diameter            │
├─────────────────────────────────────────────────────────────────────┤
│ Calculation path and assumptions                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Bracket-specific visuals

1. **Moment arm visual**
   - Show `M = P*e` directly on the diagram.

2. **Bolt group load map**
   - Highlight the most loaded bolt.
   - Show direct shear and moment tension separately if possible.

3. **Controlling constraint badge**
   - Plate bending.
   - Bolt load.
   - Deflection.

4. **Fix recommendation panel**
   - If plate bending controls: increase thickness/width, change material, reduce offset.
   - If bolt controls: increase bolt diameter/count/spacing or allowable.
   - If deflection controls: increase stiffness or reduce offset.

---

## 10. Visual style guide

## 10.1 Overall feel

Use a serious engineering aesthetic:

- Clean.
- High contrast.
- Minimal but not empty.
- Technical without being ugly.
- Visual first, details second.

## 10.2 Suggested palette

Use consistent semantic colors:

- Background: dark navy or very light gray.
- Primary accent: cyan/blue for engineering UI.
- Success: green for safe/pass.
- Warning: amber for near limit.
- Danger: red for unsafe/fail.
- Neutral: slate/gray for inactive elements.
- Stress gradient: blue/green/yellow/orange/red.

### Important

Do not make everything colorful. Reserve color for engineering meaning:

- Safety.
- Stress intensity.
- Selected design.
- Recommended design.
- Warnings.

## 10.3 Typography

Use a modern technical pairing:

- Headings: Inter, Manrope, or Space Grotesk.
- Body: Inter or system sans-serif.
- Numbers/code/equations: JetBrains Mono, IBM Plex Mono, or similar.

## 10.4 Card design

Cards should have:

- Short title.
- One dominant number.
- Unit.
- Status.
- Tiny explanation.

Example:

```text
┌─────────────────────────────┐
│ Factor of Safety            │
│ 2.41                        │
│ Target: 2.00 | PASS         │
│ Margin: +20.5%              │
└─────────────────────────────┘
```

## 10.5 Units

Every number should show units.

Examples:

- Load: N.
- Length/span: m or mm.
- Stress: MPa.
- Deflection: mm.
- Weight: kg.
- Cost: currency.
- Moment of inertia: m^4.

Unit clarity is part of UI quality in engineering software.

---

## 11. Existing site improvement matrix

| Reference | What they do well | Where MechOpt can be better | Concrete improvement |
|---|---|---|---|
| SkyCiv | Beam modeling, supports, loads, SFD/BMD/deflection/stress results | More optimization-first and beginner-friendly | Put recommendation, Pareto plot, and “why this won” above full tables |
| Calcs.com | Transparent equations, checks, detailed mode, reports | More visual and less document-heavy | Link formulas directly to diagrams and highlighted geometry |
| SimScale | Professional CAE feel, cloud simulation polish, visual analysis | Faster, simpler, no mesh/setup burden | Add simulation-lite visuals: deflected shape, stress strip, validation card |
| Onshape | CAD-like workspace, visual model canvas, design alternatives | Analysis and optimization are not the main focus | Use CAD-like layout but focus on mechanical design screening |
| Mobbin | Modern product UI patterns and real-world dashboard inspiration | Not engineering-specific | Use cards, filters, flows, and empty states while keeping engineering visuals custom |

---

## 12. Feature priority list

## Priority 1: Highest impact, easiest to show

1. **Live beam SVG diagram**
   - Force arrow, supports, length, section label.

2. **Bracket SVG diagram**
   - Wall, plate, bracket arm, force, offset, bolt group.

3. **Recommendation hero card**
   - Big safe/unsafe status.
   - Best design.
   - FoS, deflection, weight, cost.
   - Why it won.

4. **Pareto plot**
   - Weight vs cost.
   - Bubble size FoS.
   - Safe/unsafe distinction.
   - Recommended design highlighted.

5. **README screenshots and GIF**
   - Optimizer flow.
   - Section editor.
   - Validation plot.

## Priority 2: Strong engineering depth

6. **Calculation drawer**
   - Formula, substituted values, result, pass/fail.

7. **Validation & Trust tab**
   - FE validation summary, plots, assumptions.

8. **Bracket failure mode cards**
   - Plate bending, bolt group, deflection.

9. **Thickness/spacing sensitivity plots**
   - Show how bracket changes affect FoS.

10. **Buckling UI integration**
   - Since buckling already exists as a library module, surface it as another pass/fail check.

## Priority 3: Portfolio wow factor

11. **Animated deflected shape**
   - Slider or subtle animation.

12. **Interactive section comparison cards**
   - Select multiple sections visually.

13. **Asymmetric sections**
   - T, L-angle, C-channel with neutral axis calculation.

14. **Technical report export**
   - PDF or Markdown report with inputs, result, equations, plots.

15. **Standalone browser UI polish**
   - Bring `index.html` closer to the Streamlit app visually.

---

## 13. Suggested repo/file organization

Add a visual layer without mixing everything into `app.py`.

```text
mechopt/
  app.py
  mechopt/
    visuals/
      __init__.py
      beam_svg.py
      bracket_svg.py
      section_svg.py
      result_cards.py
      pareto.py
      theme.py
    ui/
      layout.py
      copy.py
      formatters.py
```

### `theme.py`

Put CSS and visual constants in one place.

```python
MECHOPT_CSS = """
<style>
/* card styles, badges, section headers, etc. */
</style>
"""
```

### `formatters.py`

Centralize units:

```python
def fmt_stress(pa):
    return f"{pa / 1e6:.2f} MPa"

def fmt_deflection(m):
    return f"{m * 1000:.2f} mm"

def fmt_weight(kg):
    return f"{kg:.2f} kg"
```

This makes the UI feel consistent.

---

## 14. Streamlit implementation checklist

## 14.1 App-level settings

Use wide layout:

```python
st.set_page_config(
    page_title="MechOpt",
    page_icon="⚙️",
    layout="wide",
)
```

## 14.2 Layout pattern

```python
left, center, right = st.columns([0.28, 0.44, 0.28])

with left:
    render_inputs()

with center:
    render_visual_model()

with right:
    render_recommendation_card()
```

## 14.3 CSS cards

Use custom cards instead of plain `st.metric` everywhere.

```python
def card(title, value, subtitle="", status="neutral"):
    st.markdown(
        f"""
        <div class="metric-card {status}">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
```

## 14.4 SVG rendering

```python
import streamlit.components.v1 as components

svg = render_beam_svg(...)
components.html(svg, height=300)
```

## 14.5 Plotly improvements

For tradeoff plots:

- Use hover labels with material, section, dimensions, FoS, weight, cost.
- Highlight recommended design.
- Add target FoS line.
- Add deflection limit marker where applicable.
- Use consistent axis labels with units.

## 14.6 Candidate table improvements

Add:

- Safe-only toggle.
- Sort by priority.
- Highlight recommended row.
- Format columns.
- Hide excessive precision.
- Put full technical columns in an expander.

Recommended visible columns:

```text
Material | Section | Dimensions | FoS | Deflection mm | Weight kg | Cost | Status
```

Technical columns in expander:

```text
Area | I | c | Stress Pa | Raw score | Constraints
```

---

## 15. Suggested landing page copy

### Hero headline

> **Optimize beams and brackets visually.**

### Subheadline

> Sweep thousands of mechanical design candidates by factor of safety, deflection, weight, and cost — then see exactly why the winning design works.

### Trust line

> Analytical beam model validated against an independent finite-element solver.

### Feature cards

```text
Beam optimization
Compare materials, sections, and dimensions under load.

Bracket analysis
Check plate bending, bolt group loading, and deflection.

Tradeoff plots
Visualize weight-cost-strength decisions with Pareto-style charts.

Transparent calculations
See formulas, assumptions, and validation notes.
```

---

## 16. Screenshot and GIF plan

The README needs visual proof. Reviewers may not clone or run the app.

### Required screenshots

1. **Hero/dashboard screenshot**
   - Show beam diagram, result card, and Pareto plot in one frame.

2. **Beam optimizer screenshot**
   - Inputs + visual beam + recommended design.

3. **Bracket analysis screenshot**
   - Bracket diagram + failure mode cards.

4. **Compare designs screenshot**
   - Top 3 candidate cards + plot.

5. **Validation screenshot**
   - FE validation plot + error card.

### Required GIF

Create a 10-15 second GIF:

1. Change load/span.
2. Beam diagram updates.
3. Click optimize.
4. Recommended design updates.
5. Pareto plot highlights winner.
6. Open calculation drawer.

### README placement

Put the GIF near the top of README, before detailed technical explanation.

Recommended README order:

1. Project title.
2. One-line summary.
3. GIF.
4. Live app link.
5. Key features.
6. Validation result.
7. Engineering case study.
8. Tech stack.
9. How to run.

---

## 17. Visual-first engineering storytelling

The site should explain the engineering visually.

## 17.1 Beam story

Show this flow:

```text
Load creates moment -> moment creates stress -> section stiffness reduces stress -> optimizer chooses efficient section
```

Visual chain:

```text
P -> M = P*L -> sigma = M*c/I -> FoS = sigma_y/sigma -> safe/unsafe
```

## 17.2 Bracket story

Show this flow:

```text
Offset load creates wall moment -> plate bends -> bolts share direct shear and moment tension -> weakest check controls
```

Visual chain:

```text
P and e -> M = P*e -> plate stress + bolt stress -> min FoS -> controlling constraint
```

## 17.3 Optimization story

Show this flow:

```text
Generate candidates -> calculate performance -> filter safe designs -> rank by priority -> recommend winner
```

Visual chain:

```text
Materials x Sections x Dimensions -> Stress/Deflection/FoS/Weight/Cost -> Safe candidates -> Best design
```

This turns the app from a calculator into a guided design tool.

---

## 18. Recommended UI states

## 18.1 Empty state

When the user first opens the app:

```text
Start by defining a load case.
MechOpt will generate candidate designs and show the safest, lightest, cheapest, or most balanced option.
```

Show a sample beam diagram even before solving.

## 18.2 Loading/solving state

```text
Evaluating candidate designs...
Materials: 6
Sections: 6
Dimensions: 10-100 mm
```

## 18.3 No safe candidate state

```text
No candidate passed your constraints.
Most likely causes:
- Target FoS is too high.
- Deflection limit is too strict.
- Load/span combination is too demanding.
- Selected sections are too small.

Try:
- Increase max dimension.
- Add I-beam or hollow sections.
- Switch to steel or titanium.
- Relax deflection limit.
```

## 18.4 Unsafe bracket state

```text
Bracket is unsafe.
Controlling constraint: plate bending.
Best fixes:
1. Increase plate thickness.
2. Reduce offset.
3. Increase plate width.
4. Use stronger material.
```

## 18.5 Near-limit state

If FoS is close to target:

```text
Passes, but with low margin.
FoS is only 4% above target. Consider increasing section size or choosing a stronger material.
```

This shows engineering judgment.

---

## 19. Engineering features that make the UI more visual

## 19.1 Add buckling as a visible check

Buckling already exists in the code but is not wired into the app UI. It should become a visible check.

Add to result cards:

```text
Yield FoS: 2.4 PASS
Deflection: 3.2 / 5.0 mm PASS
Buckling FoS: 4.8 PASS
```

Add visual:

```text
Column/buckling mode sketch:
straight line -> bowed line
```

This is especially useful if you later support columns/compressive members.

## 19.2 Add asymmetric sections visually

Future sections:

- T-section.
- L-angle.
- C-channel.

Visual opportunity:

- Show centroid shift.
- Show neutral axis not at mid-height.
- Show different `c_top` and `c_bottom`.
- Show parallel-axis theorem in calculation drawer.

This would be a very impressive mechanical engineering depth upgrade.

## 19.3 Add manufacturability badges

Optional but useful:

```text
Manufacturing notes
[Easy to machine] [Common stock] [3D-printable] [Welded/fabricated]
```

Do not overclaim cost/manufacturing accuracy. Keep it as qualitative notes unless backed by data.

---

## 20. Recommended visual roadmap

## Week 1: Make the app visually credible

- Add global CSS theme.
- Add beam SVG diagram.
- Add bracket SVG diagram.
- Add recommendation hero cards.
- Reformat tables and units.
- Add screenshots to README.

## Week 2: Make the app engineering-impressive

- Add Pareto plot.
- Add calculation drawer.
- Add validation tab.
- Add bracket failure mode cards.
- Add thickness/bolt spacing sensitivity plot.

## Week 3: Make the app portfolio-standout

- Wire buckling into UI.
- Add compare design cards.
- Add GIF.
- Add “why this won” explanations.
- Add no-safe-design suggestions.

## Week 4: Make the app advanced

- Add asymmetric sections.
- Add technical report export.
- Add neutral-axis visualization.
- Add section efficiency ranking.
- Improve standalone `index.html` parity and style.

---

## 21. Detailed feature acceptance criteria

### Beam diagram acceptance criteria

- User can identify support type visually.
- User can see load position and direction.
- User can see span length.
- User can see selected material and section.
- After solve, user can see deflected shape.
- Critical stress region is visually marked.

### Bracket diagram acceptance criteria

- User can see wall, bracket arm, load, and offset.
- User can see bolt pattern.
- Worst bolt is highlighted.
- Controlling failure mode is visible.
- Safe/unsafe status is visible without scrolling.

### Recommendation card acceptance criteria

- Shows selected best design.
- Shows FoS, deflection, weight, cost.
- Shows pass/fail state.
- Explains why design won.
- Gives next action if unsafe/no safe design.

### Pareto plot acceptance criteria

- Safe and unsafe designs are visually distinct.
- Recommended design is highlighted.
- Hover shows material, section, dimensions, FoS, weight, cost.
- Axes have units.
- Plot supports decision-making, not just decoration.

### Calculation drawer acceptance criteria

- Shows equation.
- Shows substituted values.
- Shows final result.
- Shows pass/fail threshold.
- Mentions assumptions.

---

## 22. Do/don't list

### Do

- Put diagrams before tables.
- Use color to communicate engineering state.
- Show units everywhere.
- Highlight the recommended design.
- Explain why a design wins.
- Show safe/unsafe clearly.
- Use validation as a trust signal.
- Keep assumptions visible.
- Make the UI demo well in screenshots.

### Don't

- Hide the best result below a DataFrame.
- Use tables as the primary interface.
- Add fake FEA visuals that imply unsupported physics.
- Overload the UI with too many plots at once.
- Use color only for decoration.
- Use unlabelled engineering values.
- Make it look like a toy app.
- Claim professional safety approval.

---

## 23. Concrete homepage/dashboard mockup

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ MechOpt                                                                    │
│ Visual mechanical design optimization for beams and brackets                │
│                                                                            │
│ [Beam Optimizer] [Bracket Analysis] [View Validation]                       │
├────────────────────────────────────────────────────────────────────────────┤
│ 2,400 candidates evaluated      FE validated      117 tests      Live demo  │
├──────────────────────┬─────────────────────────────┬───────────────────────┤
│ Beam Optimization     │ Bracket Analysis             │ Tradeoff Explorer     │
│ Pick load case,       │ Check plate bending,         │ Compare weight, cost, │
│ materials, sections   │ bolt load, deflection        │ FoS, and deflection   │
├──────────────────────┴─────────────────────────────┴───────────────────────┤
│ Visual preview: beam with load, bracket with bolts, Pareto plot screenshot   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 24. What to build first

If only doing one redesign pass, build these five things:

1. **Beam SVG visual canvas.**
2. **Bracket SVG visual canvas.**
3. **Big recommendation card with why-it-won.**
4. **Pareto tradeoff plot.**
5. **README GIF showing the tool visually.**

These give the largest first-impression improvement.

---

## 25. Final design philosophy

MechOpt should not try to out-feature SkyCiv, SimScale, or Onshape. Instead, it should be more focused:

> SkyCiv analyzes beams.  
> Calcs.com documents calculations.  
> SimScale simulates physics.  
> Onshape models geometry.  
> **MechOpt should visually explain mechanical design tradeoffs and recommend the best safe design.**

That is the niche.

Make every screen answer:

1. What am I analyzing?
2. What loads are applied?
3. What fails first?
4. What design is best?
5. Why is it best?
6. What tradeoff did I make?
7. Can I trust the calculation?

If the UI answers those questions visually, the site will feel much stronger than a normal calculator.

---

## 26. Reference links

Use these as design references:

- SkyCiv Beam Calculator: https://skyciv.com/free-beam-calculator/
- Calcs.com / ClearCalcs: https://calcs.com/
- SimScale Product Overview: https://www.simscale.com/product/
- Onshape Product/Data Management: https://www.onshape.com/en/features/product-data-management
- Mobbin UI Inspiration: https://mobbin.com/

Use the project context file as the implementation source of truth for MechOpt’s current modules, roadmap, validation status, and known open items.

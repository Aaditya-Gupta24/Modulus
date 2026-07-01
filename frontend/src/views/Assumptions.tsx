import Panel from '../components/Panel';
import './View.css';
import './Assumptions.css';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type Scope = 'beam' | 'bracket' | 'both';
type AssumptionKind = 'limitation' | 'design-choice';

interface AssumptionItem {
  title: string;
  detail: string;
  scope: Scope;
  kind: AssumptionKind;
}

// ─────────────────────────────────────────────
// Data
// ─────────────────────────────────────────────

const BEAM_ASSUMPTIONS: AssumptionItem[] = [
  {
    title:  'Linear-elastic material behavior (Hooke\u2019s law)',
    detail: 'Factor of safety is computed against yield stress. Post-yield behavior, plasticity, and creep are not modeled.',
    scope:  'beam',
    kind:   'design-choice',
  },
  {
    title:  'Small deflections (Euler-Bernoulli theory, no geometric nonlinearity)',
    detail: 'Plane sections remain plane; shear deformation is neglected. Error rises to ~3 % for deep beams (L/h < 5). Validated against FE.',
    scope:  'beam',
    kind:   'design-choice',
  },
  {
    title:  'Prismatic cross-section (constant along span)',
    detail: 'Section properties are uniform along the beam length. Tapered, stepped, or notched beams are not supported.',
    scope:  'beam',
    kind:   'limitation',
  },
  {
    title:  'Single-axis bending only (symmetric sections, c = h/2)',
    detail: 'All sections are symmetric about the bending axis. Weak-axis bending and biaxial bending are not modeled.',
    scope:  'beam',
    kind:   'limitation',
  },
  {
    title:  'No lateral-torsional buckling',
    detail: 'Lateral-torsional buckling (LTB) is not checked. For unbraced I-beams with large spans, LTB may govern before bending yield.',
    scope:  'beam',
    kind:   'limitation',
  },
];

const BRACKET_ASSUMPTIONS: AssumptionItem[] = [
  {
    title:  'Rigid wall attachment (infinite wall stiffness)',
    detail: 'The wall is treated as infinitely rigid. Compliance of the wall or anchor substrate is not considered.',
    scope:  'bracket',
    kind:   'design-choice',
  },
  {
    title:  'Plate modeled as cantilever beam (uniform bending)',
    detail: 'Bracket plate is treated as a cantilever beam loaded at the tip. Out-of-plane effects and gussets are not modeled.',
    scope:  'bracket',
    kind:   'design-choice',
  },
  {
    title:  'Bolt group: elastic analysis (prying neglected)',
    detail: 'Assumes rigid bracket and elastic bolt group distribution. Prying action, pre-tension, friction, and fatigue are not modeled.',
    scope:  'bracket',
    kind:   'limitation',
  },
  {
    title:  'No weld modeling',
    detail: 'Welds are not sized or checked. The model assumes bolted connections only.',
    scope:  'bracket',
    kind:   'limitation',
  },
  {
    title:  'Wall anchorage not checked',
    detail: 'Adequacy of the anchor system (concrete embedment, masonry, etc.) is outside the scope of this tool.',
    scope:  'bracket',
    kind:   'limitation',
  },
];

const GENERAL_ASSUMPTIONS: AssumptionItem[] = [
  {
    title:  'No fatigue, corrosion, dynamic, or thermal effects',
    detail: 'All analyses are static and monotonic. Cyclic loading, environmental degradation, and temperature changes are not considered.',
    scope:  'both',
    kind:   'limitation',
  },
  {
    title:  'No code compliance claims (not a structural approval tool)',
    detail: 'Results should not be used for code-compliant design or structural approval without independent engineering review.',
    scope:  'both',
    kind:   'limitation',
  },
  {
    title:  'Deterministic inputs (uncertainty via optional Monte Carlo)',
    detail: 'Default analysis uses nominal values. Enable Monte Carlo mode in the Beam Optimizer to quantify uncertainty in load and geometry inputs.',
    scope:  'both',
    kind:   'design-choice',
  },
];

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

const KIND_ICON: Record<AssumptionKind, string> = {
  limitation:    '\u26a0',  // ⚠
  'design-choice': '\u2139', // ℹ
};

const KIND_TITLE: Record<AssumptionKind, string> = {
  limitation:    'Limitation',
  'design-choice': 'Design choice',
};

const SCOPE_LABEL: Record<Scope, string> = {
  beam:    'Beam',
  bracket: 'Bracket',
  both:    'Both',
};

// ─────────────────────────────────────────────
// AssumptionCard
// ─────────────────────────────────────────────

function AssumptionCard({ item }: { item: AssumptionItem }) {
  return (
    <Panel>
      <div className="assumptions__card-inner">
        <div className="assumptions__card-left">
          <span
            className="assumptions__card-type-icon"
            title={KIND_TITLE[item.kind]}
            aria-label={KIND_TITLE[item.kind]}
          >
            {KIND_ICON[item.kind]}
          </span>
          <div className="assumptions__card-text">
            <p className="assumptions__card-title">{item.title}</p>
            <p className="assumptions__card-detail">{item.detail}</p>
          </div>
        </div>
        <span className={`assumptions__scope-badge assumptions__scope-badge--${item.scope}`}>
          {SCOPE_LABEL[item.scope]}
        </span>
      </div>
    </Panel>
  );
}

// ─────────────────────────────────────────────
// Group
// ─────────────────────────────────────────────

function AssumptionGroup({
  title,
  items,
}: {
  title: string;
  items: AssumptionItem[];
}) {
  return (
    <section className="assumptions__group" aria-labelledby={`group-${title}`}>
      <div className="assumptions__group-header">
        <span id={`group-${title}`} className="assumptions__group-title">{title}</span>
        <div className="assumptions__group-rule" aria-hidden="true" />
      </div>
      <div className="assumptions__stack">
        {items.map((item, i) => (
          <AssumptionCard key={i} item={item} />
        ))}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
// Root Component
// ─────────────────────────────────────────────

export default function Assumptions() {
  return (
    <div className="view">
      <div className="view__header">
        <p className="overline">Model documentation</p>
        <h1 className="view__title">Assumptions &amp; Limitations</h1>
        <p className="view__subtitle">
          Engineering decisions, model boundaries, and known approximations. Read before
          using results for design sign-off.&nbsp;
          <span style={{ color: 'var(--warn)' }}>&#9888;</span>&nbsp;= limitation,&nbsp;
          <span style={{ color: 'var(--accent)' }}>&#8505;</span>&nbsp;= design choice.
        </p>
      </div>

      <AssumptionGroup title="Beam Model"   items={BEAM_ASSUMPTIONS}    />
      <AssumptionGroup title="Bracket Model" items={BRACKET_ASSUMPTIONS} />
      <AssumptionGroup title="General"       items={GENERAL_ASSUMPTIONS} />
    </div>
  );
}

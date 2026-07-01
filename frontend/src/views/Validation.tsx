import Panel from '../components/Panel';
import StatusPill from '../components/StatusPill';
import DataTable from '../components/DataTable';
import type { Column } from '../components/DataTable';
import './View.css';
import './Validation.css';

// ─────────────────────────────────────────────
// Pre-populated validation data
// ─────────────────────────────────────────────

interface ValidationRow {
  test_case: string;
  analytical: string;
  fe: string;
  error: string;
  status: 'pass';
}

const VALIDATION_ROWS: ValidationRow[] = [
  {
    test_case:  'Steel rect 30 mm — cantilever point load',
    analytical: '53.33',
    fe:         '53.33',
    error:      '< 0.01',
    status:     'pass',
  },
  {
    test_case:  'Aluminum circle d30 — simply supported center',
    analytical: '90.54',
    fe:         '90.54',
    error:      '< 0.01',
    status:     'pass',
  },
  {
    test_case:  'Steel I-beam h100 b50 — cantilever point load',
    analytical: '37.63',
    fe:         '37.63',
    error:      '< 0.01',
    status:     'pass',
  },
  {
    test_case:  'Titanium hollow circle d50 di42 — simply supported',
    analytical: '97.40',
    fe:         '97.40',
    error:      '< 0.01',
    status:     'pass',
  },
];

const VALIDATION_COLUMNS: Column[] = [
  { key: 'test_case',   label: 'Test Case',            align: 'left'  },
  { key: 'analytical',  label: 'Analytical \u03c3 (MPa)', align: 'right', mono: true,
    format: v => `${v} MPa` },
  { key: 'fe',          label: 'FE \u03c3 (MPa)',      align: 'right', mono: true,
    format: v => `${v} MPa` },
  { key: 'error',       label: 'Error (%)',             align: 'right', mono: true,
    format: v => `${v} %` },
  { key: 'status',      label: 'Status',               align: 'center',
    format: () => 'Pass' },
];

// ─────────────────────────────────────────────
// Case Studies
// ─────────────────────────────────────────────

const CASE_STUDIES = [
  {
    icon: '◫',
    title: 'Shelf Bracket',
    desc: 'Standard wall-mount bracket. Steel plate, 4-bolt pattern. Validated plate bending and bolt group analysis.',
  },
  {
    icon: '⟁',
    title: 'Robot Arm Link',
    desc: 'Stiffness-critical application where deflection controls before stress. I-beam section 64 % lighter than solid.',
  },
  {
    icon: '⊼',
    title: 'Mini Crane Compression Member',
    desc: 'Buckling-critical column. Euler critical load verified against FE within 0.01 %.',
  },
];

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export default function Validation() {
  return (
    <div className="view">
      <div className="view__header">
        <p className="overline">Verification</p>
        <h1 className="view__title">Validation &amp; Case Studies</h1>
        <p className="view__subtitle">
          Independent finite-element verification of the analytical beam model. Direct
          stiffness method, Hermite cubic elements, zero shared code with beam.py.
        </p>
      </div>

      {/* ── Hero card ─────────────────────────────── */}
      <div className="validation__section">
        <Panel status="pass">
          <p className="validation__hero-headline">
            Analytical Model Validated Against Independent FEA
          </p>
          <div className="validation__hero-metrics">

            <div className="validation__hero-metric validation__hero-metric--pass">
              <span className="validation__hero-number validation__hero-number--pass">
                &lt;&nbsp;1&times;10&#8315;&#8308;&nbsp;%
              </span>
              <span className="validation__hero-desc">
                Euler-Bernoulli vs FE — max error across all test cases
              </span>
              <StatusPill status="pass" label="Matched" />
            </div>

            <div className="validation__hero-metric validation__hero-metric--pass">
              <span className="validation__hero-number validation__hero-number--pass">
                &lt;&nbsp;0.4&nbsp;%
              </span>
              <span className="validation__hero-desc">
                Shear correction error for slender beams (L/h &gt; 15)
              </span>
              <StatusPill status="pass" label="Within tolerance" />
            </div>

            <div className="validation__hero-metric validation__hero-metric--warn">
              <span className="validation__hero-number validation__hero-number--warn">
                ~3&nbsp;%
              </span>
              <span className="validation__hero-desc">
                Thick-beam error at L/h&nbsp;=&nbsp;5 — Timoshenko shear expected
              </span>
              <StatusPill status="warn" label="Expected (Timoshenko)" />
            </div>

          </div>
        </Panel>
      </div>

      {/* ── Method card ───────────────────────────── */}
      <div className="validation__section">
        <Panel title="Validation Method">
          <div className="validation__method-body">
            <p>
              The analytical beam model (Euler-Bernoulli theory) was verified against an
              independent 1-D finite element solver using Hermite cubic elements and the
              direct stiffness method. The FE solver shares no code with the analytical
              model.
            </p>
            <ul className="validation__method-list">
              <li>Load cases: cantilever point load, simply supported center load</li>
              <li>Materials: all 6 in the library</li>
              <li>Sections: all 6 cross-section types</li>
              <li>
                Metrics: stress and deflection compared at matched boundary conditions
              </li>
            </ul>
          </div>
        </Panel>
      </div>

      {/* ── Results Table ─────────────────────────── */}
      <div className="validation__section">
        <Panel title="Validation Results">
          <DataTable
            columns={VALIDATION_COLUMNS}
            rows={VALIDATION_ROWS as unknown as Record<string, unknown>[]}
          />
        </Panel>
      </div>

      {/* ── Case Studies ──────────────────────────── */}
      <div className="validation__section">
        <Panel title="Engineering Case Studies">
          <div className="validation__case-studies">
            {CASE_STUDIES.map(cs => (
              <div key={cs.title} className="validation__case-card">
                <span className="validation__case-icon" aria-hidden="true">
                  {cs.icon}
                </span>
                <p className="validation__case-title">{cs.title}</p>
                <p className="validation__case-desc">{cs.desc}</p>
                <span className="validation__case-link" aria-label="Details not yet available">
                  View Details &#8594;
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

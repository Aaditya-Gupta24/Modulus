import { useEffect, useState } from 'react';
import Panel from '../components/Panel';
import { api } from '../api';
import './View.css';
import './Compare.css';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type CompareTab = 'objective' | 'materials' | 'tradeoff';

interface Material {
  key: string;
  name: string;
  E: number;
  sigma_y: number;
  rho: number;
  cost: number;
}

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const SUBTABS: { id: CompareTab; label: string }[] = [
  { id: 'objective', label: 'By Objective' },
  { id: 'materials', label: 'Materials' },
  { id: 'tradeoff',  label: 'Tradeoff Space' },
];

const MATERIAL_COLORS: Record<string, string> = {
  aluminum_6061:     '#3b82f6',
  steel_a36:         '#6b7280',
  pla:               '#10b981',
  titanium_ti6al4v:  '#8b5cf6',
  brass_360:         '#f59e0b',
  abs_plastic:       '#ef4444',
};

const WINNER_CARDS = [
  { id: 'lightest',  icon: '⚖',  label: 'Lightest Winner',  metricLabel: 'Weight',       unit: 'kg'   },
  { id: 'cheapest',  icon: '$',   label: 'Cheapest Winner',  metricLabel: 'Cost',          unit: '$/kg' },
  { id: 'safest',    icon: '⛨',  label: 'Safest Winner',    metricLabel: 'Factor of Safety', unit: ''  },
  { id: 'balanced',  icon: '⊜',  label: 'Balanced Winner',  metricLabel: 'Score',         unit: ''     },
];


// ─────────────────────────────────────────────
// Sub-tab: By Objective
// ─────────────────────────────────────────────

function TabObjective() {
  return (
    <div className="view__grid view__grid--4">
      {WINNER_CARDS.map(card => (
        <Panel key={card.id} title={card.label}>
          <div className="compare__winner-card">
            <div className="compare__winner-ghost">
              <span className="compare__winner-ghost-icon" aria-hidden="true">
                {card.icon}
              </span>
              <p className="compare__winner-ghost-text">
                Run the Beam Optimizer first to populate this card.
              </p>
            </div>
          </div>
        </Panel>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Sub-tab: Materials
// ─────────────────────────────────────────────

function TabMaterials() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    (api.getMaterials() as Promise<Material[]>)
      .then(data => {
        setMaterials(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <Panel>
        <p style={{ color: 'var(--text-low)', fontSize: 13, padding: 'var(--space-4) 0' }}>
          Loading materials&hellip;
        </p>
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel status="fail">
        <p style={{ color: 'var(--fail)', fontSize: 13 }}>
          Could not load materials — backend offline.
        </p>
      </Panel>
    );
  }

  return (
    <Panel title="6-Material Reference Table">
      {/* Custom table instead of DataTable so we can color material names */}
      <table
        style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}
        aria-label="6-material reference table"
      >
        <thead>
          <tr>
            {[
              { label: 'Material', right: false },
              { label: '\u03c3_y (MPa)', right: true },
              { label: 'E (GPa)', right: true },
              { label: '\u03c1 (kg/m\u00b3)', right: true },
              { label: 'Cost ($/kg)', right: true },
            ].map(h => (
              <th
                key={h.label}
                style={{
                  textAlign: h.right ? 'right' : 'left',
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  color: 'var(--text-low)',
                  padding: '0 8px 12px 8px',
                  borderBottom: '1px solid var(--stroke)',
                }}
              >
                {h.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {materials.map((mat, i) => (
            <tr key={mat.key} style={{ background: i % 2 === 1 ? 'var(--bg-panel-2)' : 'transparent' }}>
              <td style={{ padding: '10px 8px' }}>
                <span className="compare__mat-cell">
                  <span
                    className="compare__mat-dot"
                    style={{ background: MATERIAL_COLORS[mat.key] ?? 'var(--neutral)' }}
                    aria-hidden="true"
                  />
                  <span style={{ fontWeight: 600, color: MATERIAL_COLORS[mat.key] ?? 'var(--text-hi)' }}>
                    {mat.name}
                  </span>
                </span>
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-hi)', padding: '10px 8px' }}>
                {(mat.sigma_y / 1e6).toFixed(0)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-hi)', padding: '10px 8px' }}>
                {(mat.E / 1e9).toFixed(0)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-hi)', padding: '10px 8px' }}>
                {mat.rho.toFixed(0)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-hi)', padding: '10px 8px' }}>
                {mat.cost.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

// ─────────────────────────────────────────────
// Sub-tab: Tradeoff Space
// ─────────────────────────────────────────────

function TabTradeoff() {
  return (
    <div className="compare__tradeoff-placeholder">
      <div className="compare__tradeoff-axes" aria-hidden="true">
        <div className="compare__tradeoff-axis-x" />
        <div className="compare__tradeoff-axis-y" />
        <span className="compare__tradeoff-axis-label compare__tradeoff-axis-label--x">
          Weight
        </span>
        <span className="compare__tradeoff-axis-label compare__tradeoff-axis-label--y">
          Cost
        </span>
      </div>
      <span className="compare__tradeoff-icon" aria-hidden="true">&#9641;</span>
      <p className="compare__tradeoff-hint">
        Save candidates from the Beam Optimizer to compare them here. The Pareto front
        will render once at least two design candidates exist.
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────
// Root Component
// ─────────────────────────────────────────────

export default function Compare() {
  const [tab, setTab] = useState<CompareTab>('objective');

  return (
    <div className="view">
      <div className="view__header">
        <p className="overline">Analysis</p>
        <h1 className="view__title">Compare</h1>
        <p className="view__subtitle">
          Side-by-side comparison of top safe candidates across weight, cost, and factor
          of safety.
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="view__subtabs" role="tablist" aria-label="Compare views">
        {SUBTABS.map(st => (
          <button
            key={st.id}
            role="tab"
            aria-selected={tab === st.id}
            className={['view__subtab', tab === st.id ? 'view__subtab--active' : ''].filter(Boolean).join(' ')}
            onClick={() => setTab(st.id)}
          >
            {st.label}
          </button>
        ))}
      </div>

      <div className="view__tab-content" key={tab}>
        {tab === 'objective' && <TabObjective />}
        {tab === 'materials' && <TabMaterials />}
        {tab === 'tradeoff'  && <TabTradeoff />}
      </div>
    </div>
  );
}

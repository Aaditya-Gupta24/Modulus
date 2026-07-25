import { useEffect, useState } from 'react';
import Panel from '../components/Panel';
import { api } from '../api';
import { loadBeamProblem } from '../store';
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

interface Candidate {
  material: string;
  section: string;
  dims: string;
  weight: number;
  cost: number;
  fos: number;
  safe: boolean;
}
interface RecommendResult { recommended: Candidate; }
interface EvaluateResult { candidates: Candidate[]; }
interface ParetoResult { front: Candidate[]; knee_point?: Candidate | null; }

const OBJECTIVES: {
  id: string; icon: string; label: string; sub: string; big: (r: Candidate) => string;
}[] = [
  { id: 'lightest', icon: '⚖', label: 'Lightest Winner', sub: 'Minimum weight',           big: r => `${r.weight.toFixed(3)} kg` },
  { id: 'cheapest', icon: '$',  label: 'Cheapest Winner', sub: 'Minimum cost',             big: r => `$${r.cost.toFixed(2)}` },
  { id: 'safest',   icon: '⛨', label: 'Safest Winner',   sub: 'Maximum factor of safety', big: r => r.fos.toFixed(2) },
  { id: 'balanced', icon: '⊜', label: 'Balanced Winner', sub: 'Factor of safety',            big: r => r.fos.toFixed(2) },
];

const prettySection = (s: string) =>
  s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());


// ─────────────────────────────────────────────
// Sub-tab: By Objective
// ─────────────────────────────────────────────

function TabObjective() {
  const [winners, setWinners] = useState<Record<string, Candidate | null>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const problem = loadBeamProblem();
    setLoading(true);
    Promise.allSettled(
      OBJECTIVES.map(o =>
        api.beamRecommend({ ...problem, priority: o.id }) as Promise<RecommendResult>,
      ),
    ).then(results => {
      const next: Record<string, Candidate | null> = {};
      results.forEach((res, i) => {
        next[OBJECTIVES[i].id] = res.status === 'fulfilled' ? res.value.recommended : null;
      });
      setWinners(next);
      setLoading(false);
    });
  }, []);

  return (
    <div className="view__grid view__grid--4">
      {OBJECTIVES.map(card => {
        const rec = winners[card.id];
        return (
          <Panel key={card.id} title={card.label}>
            <div className="compare__winner-card">
              {loading ? (
                <div className="compare__winner-ghost">
                  <span className="compare__winner-ghost-icon" aria-hidden="true">{card.icon}</span>
                  <p className="compare__winner-ghost-text">Computing&hellip;</p>
                </div>
              ) : rec ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 26, fontWeight: 700, color: 'var(--accent)' }}>
                    {card.big(rec)}
                  </span>
                  <span style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-low)' }}>
                    {card.sub}
                  </span>
                  <span style={{ fontWeight: 600, color: 'var(--text-hi)', marginTop: 4 }}>{rec.material}</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-low)' }}>
                    {prettySection(rec.section)} · {rec.dims}
                  </span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--text-low)', marginTop: 2 }}>
                    FoS {rec.fos.toFixed(2)} · {rec.weight.toFixed(2)} kg · ${rec.cost.toFixed(2)}
                  </span>
                </div>
              ) : (
                <div className="compare__winner-ghost">
                  <span className="compare__winner-ghost-icon" aria-hidden="true">{card.icon}</span>
                  <p className="compare__winner-ghost-text">No safe design for the current problem.</p>
                </div>
              )}
            </div>
          </Panel>
        );
      })}
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

function ParetoChart({ candidates, front, knee }: {
  candidates: Candidate[]; front: Candidate[]; knee: Candidate | null;
}) {
  const safe = candidates.filter(c => c.safe && isFinite(c.weight) && isFinite(c.cost));
  if (safe.length === 0) {
    return (
      <Panel title="Weight–Cost Tradeoff">
        <p style={{ color: 'var(--text-low)', fontSize: 13, padding: 'var(--space-4) 0' }}>
          No safe designs to plot for the current problem.
        </p>
      </Panel>
    );
  }

  const W = 560, H = 360;
  const pad = { l: 64, r: 24, t: 20, b: 48 };
  const xs = safe.map(c => c.weight), ys = safe.map(c => c.cost);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);
  const sx = (w: number) => pad.l + (W - pad.l - pad.r) * (xmax === xmin ? 0.5 : (w - xmin) / (xmax - xmin));
  const sy = (c: number) => H - pad.b - (H - pad.t - pad.b) * (ymax === ymin ? 0.5 : (c - ymin) / (ymax - ymin));

  const frontSorted = [...front]
    .filter(f => isFinite(f.weight) && isFinite(f.cost))
    .sort((a, b) => a.weight - b.weight);
  const linePts = frontSorted.map(f => `${sx(f.weight).toFixed(1)},${sy(f.cost).toFixed(1)}`).join(' ');

  const xticks = [xmin, (xmin + xmax) / 2, xmax];
  const yticks = [ymin, (ymin + ymax) / 2, ymax];

  return (
    <Panel title="Weight–Cost Tradeoff (Pareto front)">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
           aria-label="Weight versus cost scatter with the Pareto front highlighted"
           style={{ maxWidth: '100%', height: 'auto' }}>
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={H - pad.b} stroke="var(--stroke)" />
        <line x1={pad.l} y1={H - pad.b} x2={W - pad.r} y2={H - pad.b} stroke="var(--stroke)" />
        {xticks.map((t, i) => (
          <g key={`x${i}`}>
            <line x1={sx(t)} y1={H - pad.b} x2={sx(t)} y2={H - pad.b + 5} stroke="var(--stroke)" />
            <text x={sx(t)} y={H - pad.b + 18} fontSize="10" fill="var(--text-low)" textAnchor="middle"
                  fontFamily="JetBrains Mono, monospace">{t.toFixed(t < 10 ? 2 : 1)}</text>
          </g>
        ))}
        {yticks.map((t, i) => (
          <g key={`y${i}`}>
            <line x1={pad.l - 5} y1={sy(t)} x2={pad.l} y2={sy(t)} stroke="var(--stroke)" />
            <text x={pad.l - 8} y={sy(t) + 3} fontSize="10" fill="var(--text-low)" textAnchor="end"
                  fontFamily="JetBrains Mono, monospace">{t.toFixed(t < 10 ? 1 : 0)}</text>
          </g>
        ))}
        <text x={(pad.l + W - pad.r) / 2} y={H - 8} fontSize="11" fill="var(--text-low)" textAnchor="middle">Weight (kg)</text>
        <text x={16} y={(pad.t + H - pad.b) / 2} fontSize="11" fill="var(--text-low)" textAnchor="middle"
              transform={`rotate(-90 16 ${(pad.t + H - pad.b) / 2})`}>Cost ($)</text>
        {safe.map((c, i) => (
          <circle key={i} cx={sx(c.weight)} cy={sy(c.cost)} r={2.5} fill="var(--text-low)" opacity={0.3} />
        ))}
        {frontSorted.length > 1 && (
          <polyline points={linePts} fill="none" stroke="var(--accent)" strokeWidth={1.5} opacity={0.85} />
        )}
        {frontSorted.map((f, i) => (
          <circle key={`f${i}`} cx={sx(f.weight)} cy={sy(f.cost)} r={3.5} fill="var(--accent)" />
        ))}
        {knee && isFinite(knee.weight) && isFinite(knee.cost) && (
          <g>
            <circle cx={sx(knee.weight)} cy={sy(knee.cost)} r={6} fill="none" stroke="var(--cyan)" strokeWidth={2} />
            <text x={sx(knee.weight) + 9} y={sy(knee.cost) + 3} fontSize="10" fill="var(--cyan)"
                  fontFamily="JetBrains Mono, monospace">knee</text>
          </g>
        )}
      </svg>
      <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12, color: 'var(--text-low)', flexWrap: 'wrap' }}>
        <span><span style={{ color: 'var(--accent)' }}>●</span> Pareto-optimal</span>
        <span><span style={{ color: 'var(--cyan)' }}>◯</span> Knee point</span>
        <span><span style={{ color: 'var(--text-low)' }}>•</span> Safe candidate</span>
        <span style={{ marginLeft: 'auto' }}>{safe.length} safe · {frontSorted.length} on front</span>
      </div>
    </Panel>
  );
}

function TabTradeoff() {
  const [data, setData] = useState<{ candidates: Candidate[]; front: Candidate[]; knee: Candidate | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const problem = loadBeamProblem();
    setLoading(true);
    Promise.all([
      api.beamEvaluate(problem) as Promise<EvaluateResult>,
      api.beamPareto(problem) as Promise<ParetoResult>,
    ]).then(([evaResult, parResult]) => {
      setData({
        candidates: evaResult.candidates ?? [],
        front: parResult.front ?? [],
        knee: parResult.knee_point ?? null,
      });
      setLoading(false);
    }).catch(() => { setError(true); setLoading(false); });
  }, []);

  if (loading) {
    return (
      <Panel>
        <p style={{ color: 'var(--text-low)', fontSize: 13, padding: 'var(--space-4) 0' }}>
          Computing tradeoff space&hellip;
        </p>
      </Panel>
    );
  }
  if (error || !data) {
    return (
      <Panel status="fail">
        <p style={{ color: 'var(--fail)', fontSize: 13 }}>Could not load candidates — backend offline.</p>
      </Panel>
    );
  }
  return <ParetoChart candidates={data.candidates} front={data.front} knee={data.knee} />;
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

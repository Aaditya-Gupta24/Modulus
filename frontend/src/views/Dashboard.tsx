import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import StatusPill from '../components/StatusPill';
import ReactiveField from '../components/ReactiveField';
import { api } from '../api';
import type { ViewId } from '../components/Sidebar';
import './View.css';
import './Dashboard.css';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface Material {
  key: string;
  name: string;
  E: number;
  sigma_y: number;
  rho: number;
  cost: number;
}

interface DashboardProps {
  onNavigate?: (id: ViewId) => void;
}

const MATERIAL_COLORS: Record<string, string> = {
  titanium_ti6al4v: '#2D7FF9',
  aluminum_6061:    '#22D3EE',
  steel_a36:        '#34D399',
  brass_360:        '#FBBF24',
  pla:              '#F87171',
  abs_plastic:      '#F43F5E',
};

const CAPABILITIES = [
  '6 materials × 6 cross-sections sweep',
  'Bending, buckling, shear failure modes',
  'Pareto-optimal design selection',
  'Monte Carlo uncertainty analysis',
  'Standard stock matching',
  'Independent FE validation (< 0.01 %)',
];

const QUICK_ACTIONS: { label: string; desc: string; target: ViewId }[] = [
  { label: 'Run an optimization', desc: 'Sweep the beam design space',      target: 'beam-optimizer' },
  { label: 'Analyze a bracket',   desc: 'Plate bending + bolt group',       target: 'bracket-analysis' },
  { label: 'Browse materials',    desc: 'Compare 6 materials side-by-side',  target: 'compare' },
  { label: 'View the validation', desc: 'FEA vs analytical results',         target: 'validation' },
];

const OBJECTIVES: { word: string; color: string }[] = [
  { word: 'lightest', color: '#22D3EE' },
  { word: 'cheapest', color: '#FBBF24' },
  { word: 'safest',   color: '#34D399' },
];

function useObjectiveRotation() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = setInterval(() => {
      setIndex(prev => (prev + 1) % OBJECTIVES.length);
    }, 2400);
    return () => clearInterval(timer);
  }, []);

  return OBJECTIVES[index];
}

// ─────────────────────────────────────────────
// Motion variants
// ─────────────────────────────────────────────

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

const rise = (y: number) => ({
  hidden: { opacity: 0, y },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
});

const fadeUp = rise(20);
const bandReveal = rise(28);

/** Scroll-revealed section band shared by all dashboard sections. */
function Band({ title, tag, children }: { title: string; tag: string; children: React.ReactNode }) {
  return (
    <motion.section
      className="dash-band"
      variants={bandReveal}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.3 }}
    >
      <h2 className="dash-band__title">{title}</h2>
      <p className="dash-band__tag">{tag}</p>
      {children}
    </motion.section>
  );
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export default function Dashboard({ onNavigate }: DashboardProps) {
  const [materials, setMaterials] = useState<Material[]>([]);
  // null = still loading, false = backend offline
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const objective = useObjectiveRotation();

  useEffect(() => {
    (api.getMaterials() as Promise<Material[]>)
      .then(data => {
        setMaterials(Array.isArray(data) ? data : []);
        setApiConnected(true);
      })
      .catch(() => setApiConnected(false));
  }, []);

  return (
    <div className="dash">
      {/* Reactive FEA stress-field — full-page backdrop behind every section */}
      <ReactiveField className="dash-field" spacing={44} />

      {/* ══ HERO — full viewport ══ */}
      <section className="dash-hero">
        <div className="dash-hero__vignette" aria-hidden="true" />

        <motion.div
          className="dash-hero__inner"
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          <motion.h1 className="dash-wordmark" variants={fadeUp}>
            Modulus
          </motion.h1>

          <motion.p className="dash-tag" variants={fadeUp}>
            Sizes beams &amp; brackets against stress, deflection &amp; buckling
          </motion.p>

          <motion.p className="dash-lede" variants={fadeUp}>
            Sweep materials and cross-sections to find the{' '}
            <span className="dash-lede__rot">
              <AnimatePresence mode="wait">
                <motion.span
                  key={objective.word}
                  className="dash-lede__word"
                  style={{ color: objective.color }}
                  initial={{ y: 12, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -12, opacity: 0 }}
                  transition={{ duration: 0.28, ease: EASE }}
                >
                  {objective.word}
                </motion.span>
              </AnimatePresence>
            </span>{' '}
            design — validated against independent FEA to {'<'}&thinsp;0.01&thinsp;%.
          </motion.p>

          <motion.div className="dash-hero__cta" variants={fadeUp}>
            <button
              type="button"
              className="dash-btn dash-btn--primary"
              onClick={() => onNavigate?.('beam-optimizer')}
            >
              Run an optimization
            </button>
            <button
              type="button"
              className="dash-btn dash-btn--ghost"
              onClick={() => onNavigate?.('validation')}
            >
              View the validation
            </button>
          </motion.div>
        </motion.div>

      </section>

      <Band title="Everything the solver checks." tag="Engine · Capabilities">
        <div className="dash-cap-grid">
          {CAPABILITIES.map((cap, i) => (
            <div key={cap} className="dash-cap">
              <span className="dash-cap__num">{String(i + 1).padStart(2, '0')}</span>
              <span className="dash-cap__text">{cap}</span>
            </div>
          ))}
        </div>
      </Band>

      <Band title="Six materials, one comparison." tag="Library · Materials">
        {apiConnected === null ? (
          <p className="dash-note">Loading materials&hellip;</p>
        ) : apiConnected === false ? (
          <p className="dash-note dash-note--hot">Backend offline — start the API server.</p>
        ) : (
          <table className="dash-mat-table" aria-label="Materials library">
            <thead>
              <tr>
                <th>Material</th>
                <th className="num">&sigma;<sub>y</sub> (MPa)</th>
                <th className="num">E (GPa)</th>
                <th className="num">&rho; (kg/m&sup3;)</th>
                <th className="num">$/kg</th>
              </tr>
            </thead>
            <tbody>
              {materials.map(mat => (
                <tr key={mat.key}>
                  <td>
                    <span
                      className="dash-mat-name"
                      style={{ color: MATERIAL_COLORS[mat.key] ?? 'var(--ink)' }}
                    >
                      {mat.name}
                    </span>
                  </td>
                  <td className="num">{(mat.sigma_y / 1e6).toFixed(0)}</td>
                  <td className="num">{(mat.E / 1e9).toFixed(0)}</td>
                  <td className="num">{mat.rho.toFixed(0)}</td>
                  <td className="num">{mat.cost.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Band>

      <Band title="Verified and online." tag="System · Status">
        <div className="dash-readout">
          <div className="dash-readout__item">
            <span className="dash-readout__label">API</span>
            {apiConnected === null ? (
              <span className="dash-readout__val">Checking&hellip;</span>
            ) : apiConnected ? (
              <span className="dash-readout__val dash-readout__val--pass">
                <span className="dash-pulse" aria-hidden="true" />Connected
              </span>
            ) : (
              <StatusPill status="fail" label="Disconnected" />
            )}
          </div>
          <div className="dash-readout__item">
            <span className="dash-readout__label">Tests</span>
            <span className="dash-readout__val dash-readout__val--pass">354 passing</span>
          </div>
          <div className="dash-readout__item">
            <span className="dash-readout__label">Engine</span>
            <span className="dash-readout__val">Python + NumPy</span>
          </div>
          <div className="dash-readout__item">
            <span className="dash-readout__label">FE error</span>
            <span className="dash-readout__val dash-readout__val--pass">&lt;&thinsp;0.01&thinsp;%</span>
          </div>
        </div>
      </Band>

      <Band title="Pick a workflow." tag="Start">
        <div className="dash-actions">
          {QUICK_ACTIONS.map(action => (
            <button
              key={action.target}
              type="button"
              className="dash-action"
              onClick={() => onNavigate?.(action.target)}
              aria-label={action.label}
            >
              <span className="dash-action__label">{action.label}</span>
              <span className="dash-action__desc">{action.desc}</span>
              <span className="dash-action__arrow" aria-hidden="true">&rarr;</span>
            </button>
          ))}
        </div>
      </Band>
    </div>
  );
}

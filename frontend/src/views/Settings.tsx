import { useEffect, useState } from 'react';
import Panel from '../components/Panel';
import StatusPill from '../components/StatusPill';
import { api } from '../api';
import './View.css';
import './Settings.css';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type UnitSystem = 'si' | 'metric' | 'imperial';

interface UnitOption {
  id: UnitSystem;
  name: string;
  desc: string;
}

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const UNIT_OPTIONS: UnitOption[] = [
  { id: 'si',       name: 'SI',       desc: 'm, N, Pa, kg' },
  { id: 'metric',   name: 'Metric',   desc: 'mm, N, MPa, kg' },
  { id: 'imperial', name: 'Imperial', desc: 'in, lbf, psi, lb' },
];

// ─────────────────────────────────────────────
// Toggle Switch helper
// ─────────────────────────────────────────────

function ToggleSwitch({
  id,
  checked,
  disabled,
  onChange,
}: {
  id: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="settings__switch" htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
      />
      <span className="settings__switch-track" />
    </label>
  );
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export default function Settings() {
  // Unit system
  const [unitSystem, setUnitSystem] = useState<UnitSystem>('metric');

  // Display preferences
  const [reduceMotion, setReduceMotion] = useState(false);
  const [showNotModeled, setShowNotModeled] = useState(true);

  // API status
  const [apiStatus, setApiStatus] = useState<'idle' | 'checking' | 'ok' | 'fail'>('idle');

  // Detect system prefers-reduced-motion on mount
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  function handleTestConnection() {
    setApiStatus('checking');
    (api.getMaterials() as Promise<unknown>)
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('fail'));
  }

  return (
    <div className="view">
      <div className="view__header">
        <p className="overline">Configuration</p>
        <h1 className="view__title">Settings</h1>
        <p className="view__subtitle">
          Unit system, display preferences, and API configuration.
        </p>
      </div>

      {/* ── Unit System ─────────────────────────── */}
      <div className="settings__section-gap">
        <Panel title="Unit System">
          <div className="settings__unit-options" role="radiogroup" aria-label="Unit system">
            {UNIT_OPTIONS.map(opt => (
              <button
                key={opt.id}
                type="button"
                role="radio"
                aria-checked={unitSystem === opt.id}
                className={[
                  'settings__unit-option',
                  unitSystem === opt.id ? 'settings__unit-option--active' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => setUnitSystem(opt.id)}
              >
                <span className="settings__unit-name">{opt.name}</span>
                <span className="settings__unit-desc">{opt.desc}</span>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      {/* ── Display Preferences ─────────────────── */}
      <div className="settings__section-gap">
        <Panel title="Display Preferences">
          <div className="settings__toggle-list">

            <div className="settings__toggle-row">
              <div className="settings__toggle-label">
                <span className="settings__toggle-label-text">Reduce motion</span>
                <span className="settings__toggle-hint">
                  Disables panel hover lifts, gauge animation, and tab transitions.
                  Follows system preference but can be overridden here.
                </span>
              </div>
              <ToggleSwitch
                id="toggle-reduce-motion"
                checked={reduceMotion}
                onChange={setReduceMotion}
              />
            </div>

            <div className="settings__toggle-row">
              <div className="settings__toggle-label">
                <span className="settings__toggle-label-text settings__toggle-label-text--disabled">
                  Compact density
                </span>
                <span className="settings__toggle-hint">
                  Tighter spacing throughout the UI. Coming in a future release.
                </span>
              </div>
              <ToggleSwitch
                id="toggle-compact"
                checked={false}
                disabled
                onChange={() => {}}
              />
            </div>

            <div className="settings__toggle-row">
              <div className="settings__toggle-label">
                <span className="settings__toggle-label-text">
                  Show not-modeled checks
                </span>
                <span className="settings__toggle-hint">
                  Display rows marked &ldquo;not modeled&rdquo; in the safety-case table
                  (e.g. fatigue, LTB). Useful for scope awareness.
                </span>
              </div>
              <ToggleSwitch
                id="toggle-not-modeled"
                checked={showNotModeled}
                onChange={setShowNotModeled}
              />
            </div>

          </div>
        </Panel>
      </div>

      {/* ── API Connection ───────────────────────── */}
      <div className="settings__section-gap">
        <Panel title="API Connection">
          <div className="settings__api-body">

            <div className="settings__api-status-row">
              <span style={{ fontSize: 13, color: 'var(--text-mid)' }}>Status</span>
              {apiStatus === 'idle' && (
                <StatusPill status="neutral" label="Not tested" />
              )}
              {apiStatus === 'checking' && (
                <StatusPill status="neutral" label="Checking\u2026" />
              )}
              {apiStatus === 'ok' && (
                <StatusPill status="pass" label="Connected" />
              )}
              {apiStatus === 'fail' && (
                <StatusPill status="fail" label="Disconnected" />
              )}
            </div>

            <div>
              <span style={{ fontSize: 12, color: 'var(--text-low)', display: 'block', marginBottom: 6 }}>
                Backend URL
              </span>
              <code className="settings__api-url">/api (proxied via Vite dev server)</code>
            </div>

            <div>
              <button
                type="button"
                className="settings__api-test-btn"
                onClick={handleTestConnection}
                disabled={apiStatus === 'checking'}
              >
                {apiStatus === 'checking' ? 'Checking\u2026' : 'Test Connection'}
              </button>
            </div>

          </div>
        </Panel>
      </div>

      {/* ── About ────────────────────────────────── */}
      <div className="settings__section-gap">
        <Panel title="About MechOpt">
          <div className="settings__about-rows">
            <div className="settings__about-row">
              <span className="settings__about-key">Version</span>
              <span className="settings__about-val settings__about-val--mono">v1.0.0</span>
            </div>
            <div className="settings__about-row">
              <span className="settings__about-key">Stack</span>
              <span className="settings__about-val">
                Python &middot; FastAPI &middot; React &middot; TypeScript
              </span>
            </div>
            <div className="settings__about-row">
              <span className="settings__about-key">Author</span>
              <span className="settings__about-val">Aaditya Gupta</span>
            </div>
            <div className="settings__about-row">
              <span className="settings__about-key">GitHub</span>
              <span className="settings__about-val settings__about-val--mono">
                github.com/Aaditya-Gupta24/MechOpt
              </span>
            </div>
            <div className="settings__about-row">
              <span className="settings__about-key">License</span>
              <span className="settings__about-val">MIT</span>
            </div>
            <div className="settings__about-row">
              <span className="settings__about-key">Tests</span>
              <span className="settings__about-val" style={{ color: 'var(--pass)' }}>
                117+ tests &middot; CI on every push
              </span>
            </div>
          </div>
        </Panel>
      </div>

    </div>
  );
}

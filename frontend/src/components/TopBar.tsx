import { useState, useCallback } from 'react';
import './TopBar.css';

type UnitSystem = 'SI' | 'MM' | 'Imperial';
type RunState = 'idle' | 'computing';

const UNIT_CYCLE: UnitSystem[] = ['SI', 'MM', 'Imperial'];

interface TopBarProps {
  viewTitle: string;
  runState?: RunState;
  showUnitChip?: boolean;
  showExport?: boolean;
  onExport?: () => void;
}

export default function TopBar({
  viewTitle,
  runState = 'idle',
  showUnitChip = true,
  showExport = true,
  onExport,
}: TopBarProps) {
  const [units, setUnits] = useState<UnitSystem>('SI');
  const [exportOpen, setExportOpen] = useState(false);

  const cycleUnits = useCallback(() => {
    setUnits(prev => {
      const idx = UNIT_CYCLE.indexOf(prev);
      return UNIT_CYCLE[(idx + 1) % UNIT_CYCLE.length];
    });
  }, []);

  const handleExportKey = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') setExportOpen(o => !o);
      if (e.key === 'Escape') setExportOpen(false);
    },
    [],
  );

  return (
    <header className="topbar">
      {/* Left: brand mark + view title */}
      <div className="topbar__left">
        <div className="topbar__brand" aria-label="MechOpt">
          <svg viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg" className="topbar__hex" aria-hidden="true">
            <polygon
              points="11,1 20,6.5 20,15.5 11,21 2,15.5 2,6.5"
              fill="var(--bg-panel-2)"
              stroke="var(--accent)"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <text x="11" y="14.5" textAnchor="middle" fontFamily="Inter, sans-serif" fontSize="7.5" fontWeight="700" fill="var(--accent)">M</text>
          </svg>
        </div>
        <span className="topbar__separator" aria-hidden="true">/</span>
        <h1 className="topbar__view-title" key={viewTitle}>
          {viewTitle}
        </h1>
      </div>

      {/* Right: conditionally show unit chip, run state, export */}
      <div className="topbar__right">
        {/* Unit system chip — only on analysis views */}
        {showUnitChip && (
          <button
            className="topbar__unit-chip"
            onClick={cycleUnits}
            aria-label={`Unit system: ${units}. Click to cycle.`}
            title="Click to cycle unit system"
          >
            <span className="topbar__unit-chip-dot" aria-hidden="true" />
            {units}
          </button>
        )}

        {/* Run state pill — always visible */}
        <div
          className={`topbar__run-pill topbar__run-pill--${runState}`}
          role="status"
          aria-live="polite"
          aria-label={runState === 'idle' ? 'Up to date' : 'Recomputing'}
        >
          <span className="topbar__run-dot" aria-hidden="true" />
          <span className="topbar__run-label">
            {runState === 'idle' ? 'Up to date' : 'Recomputing\u2026'}
          </span>
        </div>

        {/* Export dropdown — only on analysis views */}
        {showExport && (
          <div className="topbar__export-wrap">
            <button
              className="topbar__export-btn"
              onClick={() => setExportOpen(o => !o)}
              onKeyDown={handleExportKey}
              aria-haspopup="menu"
              aria-expanded={exportOpen}
              aria-label="Export report"
            >
              <span aria-hidden="true">&#8613;</span>
              Export
              <span className="topbar__export-chevron" aria-hidden="true">
                {exportOpen ? '\u25B2' : '\u25BC'}
              </span>
            </button>

            {exportOpen && (
              <div className="topbar__export-menu" role="menu" aria-label="Export options">
                <button
                  className="topbar__export-option"
                  role="menuitem"
                  onClick={() => { onExport?.(); setExportOpen(false); }}
                >
                  PDF Report
                </button>
                <button
                  className="topbar__export-option"
                  role="menuitem"
                  onClick={() => { setExportOpen(false); }}
                >
                  CSV Data
                </button>
                <button
                  className="topbar__export-option"
                  role="menuitem"
                  onClick={() => { setExportOpen(false); }}
                >
                  JSON Snapshot
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

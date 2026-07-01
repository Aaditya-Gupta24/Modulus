import { useState, useCallback } from 'react';
import Panel from '../components/Panel';
import StatusPill from '../components/StatusPill';
import MarginMeter from '../components/MarginMeter';
import { api } from '../api';
import './View.css';
import './BeamOptimizer.css';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type BeamTab = 'setup' | 'results' | 'tradeoffs' | 'design-review';

interface CheckRow {
  name: string;
  actual: number;
  allowable: number;
  margin: number;
  status: 'pass' | 'warn' | 'fail' | 'not_modeled';
  notes: string;
}

interface SafetyCase {
  checks: CheckRow[];
  overall_status: string;
  controlling_check: string;
  failure_reasons: string[];
}

interface CandidateRow {
  material: string;
  section: string;
  dims: string;
  weight: number;
  cost: number;
  fos: number;
  stress: number;
  deflection: number;
  safe: boolean;
  rank?: number;
  safety_case?: SafetyCase;
}

interface RecommendResult {
  recommended: CandidateRow & {
    area: number;
    I: number;
    safety_case: SafetyCase;
  };
}

interface RankResult {
  ranked: CandidateRow[];
  infeasible_reasons: Record<string, string>;
}

interface ParetoResult {
  front: CandidateRow[];
  knee_index: number;
  knee_point: CandidateRow;
}

interface SensitivityRow {
  parameter: string;
  baseline_value: number;
  bumped_value: number;
  fos_change: number;
  deflection_change: number;
}

interface ReviewResult {
  recommended: CandidateRow;
  why_it_won: string;
  controlling_constraint: string;
  controlling_margin: number;
  sensitivities: SensitivityRow[];
  most_important_sensitivity: string;
  unmodeled_risks: string[];
  nearest_alternative: string;
  recommended_next_step: string;
}

interface AllResults {
  recommend: RecommendResult;
  rank: RankResult;
  pareto: ParetoResult;
  review: ReviewResult;
}

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const TABS: { id: BeamTab; label: string }[] = [
  { id: 'setup',         label: 'Setup' },
  { id: 'results',       label: 'Results' },
  { id: 'tradeoffs',     label: 'Tradeoffs' },
  { id: 'design-review', label: 'Design Review' },
];

const ALL_MATERIALS = [
  { id: 'aluminum_6061',     label: 'Aluminum',  color: '#3b82f6' },
  { id: 'steel_a36',         label: 'Steel',     color: '#6b7280' },
  { id: 'pla',               label: 'PLA',       color: '#10b981' },
  { id: 'titanium_ti6al4v',  label: 'Titanium',  color: '#8b5cf6' },
  { id: 'brass_360',         label: 'Brass',     color: '#f59e0b' },
  { id: 'abs_plastic',       label: 'ABS',       color: '#ef4444' },
];

const ALL_SECTIONS = [
  { id: 'rectangle',         label: 'Rectangle' },
  { id: 'circle',            label: 'Circle' },
  { id: 'i_beam',            label: 'I-Beam' },
  { id: 'hollow_rectangle',  label: 'Hollow Rect' },
  { id: 'square_tube',       label: 'Square Tube' },
  { id: 'hollow_circle',     label: 'Hollow Circle' },
];

const LOAD_CASES = [
  {
    id: 'cantilever_end',
    label: 'Cantilever End Load',
    description: 'Point load at free tip',
  },
  {
    id: 'cantilever_udl',
    label: 'Cantilever UDL',
    description: 'Distributed load, fixed root',
  },
  {
    id: 'simply_center',
    label: 'Simply Supported Center',
    description: 'Point load at midspan',
  },
  {
    id: 'simply_udl',
    label: 'Simply Supported UDL',
    description: 'Distributed load, pinned ends',
  },
];

const PRIORITY_OPTIONS = [
  { value: 'lightest',  label: 'Lightest' },
  { value: 'cheapest',  label: 'Cheapest' },
  { value: 'safest',    label: 'Safest' },
  { value: 'balanced',  label: 'Balanced' },
];

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 3): string {
  if (n == null || !isFinite(n)) return 'N/A';
  return n.toFixed(decimals);
}

function fmtSI(n: number | undefined | null, unit: string, decimals = 2): string {
  if (n == null || !isFinite(n)) return 'N/A';
  if (Math.abs(n) >= 1e6)  return `${(n / 1e6).toFixed(decimals)} M${unit}`;
  if (Math.abs(n) >= 1e3)  return `${(n / 1e3).toFixed(decimals)} k${unit}`;
  return `${n.toFixed(decimals)} ${unit}`;
}

function checkLabel(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function statusToPanel(s: string): 'pass' | 'warn' | 'fail' | 'neutral' {
  if (s === 'pass') return 'pass';
  if (s === 'fail') return 'fail';
  if (s === 'warn') return 'warn';
  return 'neutral';
}

// ─────────────────────────────────────────────
// Inline sub-components (no file split per spec)
// ─────────────────────────────────────────────

// ---- InputGroup ----
interface InputGroupProps {
  label: string;
  unit?: string;
  value: number;
  onChange: (v: number) => void;
  type?: string;
  min?: number;
  max?: number;
  step?: number;
  helperText?: string;
}
function InputGroup({ label, unit, value, onChange, type = 'number', min, max, step, helperText }: InputGroupProps) {
  return (
    <div className="beam-input-group">
      <label className="beam-input-group__label label">
        {label}
        {unit && <span className="beam-input-group__unit">{unit}</span>}
      </label>
      <input
        className="beam-input-group__input"
        type={type}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
      />
      {helperText && <p className="beam-input-group__helper">{helperText}</p>}
    </div>
  );
}

// ---- SegmentedToggle ----
interface SegmentedToggleProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  label?: string;
}
function SegmentedToggle({ options, value, onChange, label }: SegmentedToggleProps) {
  return (
    <div className="beam-seg-toggle">
      {label && <span className="beam-seg-toggle__label label">{label}</span>}
      <div className="beam-seg-toggle__row">
        {options.map(opt => (
          <button
            key={opt.value}
            className={`beam-seg-toggle__btn${value === opt.value ? ' beam-seg-toggle__btn--active' : ''}`}
            onClick={() => onChange(opt.value)}
            type="button"
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---- ChipSelector ----
interface ChipSelectorProps {
  chips: { id: string; label: string; color?: string }[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label?: string;
}
function ChipSelector({ chips, selected, onChange, label }: ChipSelectorProps) {
  function toggle(id: string) {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id));
    } else {
      onChange([...selected, id]);
    }
  }
  return (
    <div className="beam-chip-sel">
      {label && <span className="beam-chip-sel__label label">{label}</span>}
      <div className="beam-chip-sel__chips">
        {chips.map(chip => {
          const active = selected.includes(chip.id);
          return (
            <button
              key={chip.id}
              type="button"
              className={`beam-chip${active ? ' beam-chip--active' : ''}`}
              onClick={() => toggle(chip.id)}
              style={active && chip.color ? { borderColor: chip.color, color: chip.color } as React.CSSProperties : undefined}
            >
              {chip.color && (
                <span
                  className="beam-chip__dot"
                  style={{ background: chip.color } as React.CSSProperties}
                />
              )}
              {chip.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---- BeamPreviewSVG ----
interface BeamPreviewProps {
  loadCase: string;
  load: number;
  length: number;
}
function BeamPreviewSVG({ loadCase, load, length }: BeamPreviewProps) {
  const W = 480;
  const H = 220;
  const beamY = 130;
  const beamX0 = 60;
  const beamX1 = W - 60;
  const beamLen = beamX1 - beamX0;

  // Clamp arrow scale
  const arrowScale = Math.min(1, Math.max(0.2, load / 2000));
  const arrowH = 44 * arrowScale;

  const isCantilever = loadCase.startsWith('cantilever');
  const isUDL = loadCase.includes('udl');

  // Deflection curve (exaggerated, visual only)
  const deflAmt = 28;
  function deflPath(): string {
    if (isCantilever) {
      // cubic from fixed left to deflected right tip
      return `M ${beamX0} ${beamY} C ${beamX0 + beamLen * 0.5} ${beamY} ${beamX1 - 20} ${beamY + deflAmt * 0.6} ${beamX1} ${beamY + deflAmt}`;
    } else {
      // parabola for simply supported: deflects at center
      return `M ${beamX0} ${beamY} Q ${beamX0 + beamLen / 2} ${beamY + deflAmt} ${beamX1} ${beamY}`;
    }
  }

  // UDL arrows — 6 evenly spaced
  function udlArrows(): React.ReactNode[] {
    const n = 6;
    const nodes: React.ReactNode[] = [];
    for (let i = 0; i < n; i++) {
      const x = beamX0 + (i + 0.5) * (beamLen / n);
      const tipY = beamY - 8;
      const baseY = tipY - 28;
      nodes.push(
        <g key={i}>
          <line x1={x} y1={baseY} x2={x} y2={tipY} stroke="var(--accent)" strokeWidth="1.5" />
          <polygon points={`${x},${tipY} ${x - 4},${tipY - 8} ${x + 4},${tipY - 8}`} fill="var(--accent)" />
        </g>
      );
    }
    return nodes;
  }

  // UDL top bar
  function udlBar(): React.ReactNode {
    return (
      <line
        x1={beamX0} y1={beamY - 36}
        x2={beamX1} y2={beamY - 36}
        stroke="var(--accent)" strokeWidth="1.5"
      />
    );
  }

  // Single center / tip arrow
  function singleArrow(): React.ReactNode {
    const x = isCantilever ? beamX1 : beamX0 + beamLen / 2;
    const tipY = beamY - 8;
    const baseY = tipY - arrowH;
    return (
      <g>
        <line x1={x} y1={baseY} x2={x} y2={tipY} stroke="var(--accent)" strokeWidth="2" />
        <polygon points={`${x},${tipY} ${x - 5},${tipY - 10} ${x + 5},${tipY - 10}`} fill="var(--accent)" />
      </g>
    );
  }

  // Fixed wall (cantilever left) — hatched rectangle + bold face line
  function fixedWall(): React.ReactNode {
    return (
      <g>
        <defs>
          <pattern id="beam-wall-hatch" width="8" height="8"
            patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="8" stroke="var(--stroke)" strokeWidth="2.5" />
          </pattern>
        </defs>
        <rect x={beamX0 - 18} y={beamY - 28} width={18} height={56}
          fill="url(#beam-wall-hatch)" rx="2" />
        <rect x={beamX0 - 18} y={beamY - 28} width={18} height={56}
          fill="var(--bg-panel-2)" opacity="0.5" rx="2" />
        {/* Bold wall face */}
        <line x1={beamX0} y1={beamY - 28} x2={beamX0} y2={beamY + 28}
          stroke="var(--text-mid)" strokeWidth="2.5" />
      </g>
    );
  }

  // Pin support
  function pinSupport(x: number): React.ReactNode {
    return (
      <g>
        <polygon
          points={`${x},${beamY + 8} ${x - 10},${beamY + 24} ${x + 10},${beamY + 24}`}
          fill="none" stroke="var(--stroke)" strokeWidth="1.5"
        />
        <line x1={x - 12} y1={beamY + 26} x2={x + 12} y2={beamY + 26} stroke="var(--stroke)" strokeWidth="1.5" />
      </g>
    );
  }

  // Roller support (pin + small wheels)
  function rollerSupport(x: number): React.ReactNode {
    return (
      <g>
        <polygon
          points={`${x},${beamY + 8} ${x - 10},${beamY + 24} ${x + 10},${beamY + 24}`}
          fill="none" stroke="var(--stroke)" strokeWidth="1.5"
        />
        <line x1={x - 12} y1={beamY + 26} x2={x + 12} y2={beamY + 26} stroke="var(--stroke)" strokeWidth="1.5" />
        <circle cx={x - 7} cy={beamY + 30} r="3" fill="none" stroke="var(--stroke)" strokeWidth="1" />
        <circle cx={x}     cy={beamY + 30} r="3" fill="none" stroke="var(--stroke)" strokeWidth="1" />
        <circle cx={x + 7} cy={beamY + 30} r="3" fill="none" stroke="var(--stroke)" strokeWidth="1" />
      </g>
    );
  }

  // Span dimension line
  function dimensionLine(): React.ReactNode {
    const dimY = beamY + 52;
    return (
      <g>
        <line x1={beamX0} y1={dimY} x2={beamX1} y2={dimY} stroke="var(--text-low)" strokeWidth="1" strokeDasharray="3 3" />
        <line x1={beamX0} y1={dimY - 5} x2={beamX0} y2={dimY + 5} stroke="var(--text-low)" strokeWidth="1" />
        <line x1={beamX1} y1={dimY - 5} x2={beamX1} y2={dimY + 5} stroke="var(--text-low)" strokeWidth="1" />
        <text x={(beamX0 + beamX1) / 2} y={dimY + 14} textAnchor="middle"
          fontSize="11" fill="var(--text-low)" fontFamily="JetBrains Mono, monospace">
          L = {length.toFixed(2)} m
        </text>
      </g>
    );
  }

  // Load case title
  const lcTitle = loadCase.replace(/_/g, ' ').toUpperCase();

  return (
    <svg
      className="beam-preview-svg"
      viewBox={`0 0 ${W} ${H}`}
      aria-label={`Beam preview: ${loadCase.replace(/_/g, ' ')}`}
    >
      {/* Background */}
      <rect width={W} height={H} rx="10" fill="var(--bg-panel-2)" />

      {/* Grid lines — subtle horizontal dashes */}
      {[40, 80, 120, 160].map(y => (
        <line key={y} x1={0} y1={y} x2={W} y2={y}
          stroke="var(--stroke-soft)" strokeWidth="0.5" strokeDasharray="4 6" opacity="0.4" />
      ))}

      {/* Title label */}
      <text x={14} y={18} fontSize="9" fill="var(--text-low)"
        fontFamily="Inter, sans-serif" fontWeight="600" letterSpacing="2" opacity="0.7">
        {lcTitle}
      </text>

      {/* Deflection curve (dashed cyan) */}
      <path d={deflPath()} fill="none" stroke="var(--cyan)" strokeWidth="1.5"
        strokeDasharray="6 4" opacity="0.55" />

      {/* Deflection label */}
      <text
        x={isCantilever ? beamX1 + 6 : beamX0 + beamLen / 2}
        y={isCantilever ? beamY + deflAmt + 4 : beamY + deflAmt + 12}
        fontSize="10" fill="var(--cyan)" opacity="0.65"
        fontFamily="JetBrains Mono, monospace"
        textAnchor={isCantilever ? 'start' : 'middle'}
      >
        {'δ'}
        <tspan fontSize="7" dy="3">max</tspan>
      </text>

      {/* Beam body */}
      <rect x={beamX0} y={beamY - 8} width={beamLen} height={16}
        rx="3" fill="var(--bg-panel)" stroke="var(--text-mid)" strokeWidth="1.8"
        opacity="0.85" />

      {/* Supports */}
      {isCantilever ? fixedWall() : (
        <>
          {pinSupport(beamX0)}
          {rollerSupport(beamX1)}
        </>
      )}

      {/* Load */}
      {isUDL ? (
        <>
          {udlBar()}
          {udlArrows()}
        </>
      ) : singleArrow()}

      {/* Load label */}
      <text
        x={isUDL ? (beamX0 + beamX1) / 2 : (isCantilever ? beamX1 : beamX0 + beamLen / 2)}
        y={isUDL ? beamY - 44 : beamY - arrowH - 8}
        textAnchor="middle" fontSize="11" fill="var(--accent)"
        fontFamily="JetBrains Mono, monospace" fontWeight="600"
      >
        {isUDL ? `q = ${(load / length).toFixed(0)} N/m` : `P = ${load} N`}
      </text>

      {/* Dimension line */}
      {dimensionLine()}

      {/* Stress gradient bar */}
      <defs>
        <linearGradient id="beam-stress-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--cyan)" stopOpacity="0.6" />
          <stop offset="50%" stopColor="#FBBF24" stopOpacity="0.6" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.8" />
        </linearGradient>
      </defs>
      <rect x={beamX0} y={H - 22} width={beamLen} height={4} rx="2"
        fill="url(#beam-stress-grad)" />
      <text x={beamX0} y={H - 10} fontSize="7" fill="var(--cyan)" opacity="0.5"
        fontFamily="JetBrains Mono, monospace">LOW {'σ'}</text>
      <text x={beamX1 - 30} y={H - 10} fontSize="7" fill="var(--accent)" opacity="0.5"
        fontFamily="JetBrains Mono, monospace">HIGH {'σ'}</text>
    </svg>
  );
}

// ---- SafetyCaseTable ----
interface SafetyCaseTableProps {
  checks: CheckRow[];
  animate?: boolean;
}
function SafetyCaseTable({ checks, animate = true }: SafetyCaseTableProps) {
  return (
    <div className="beam-sct">
      <div className="beam-sct__head">
        <span>Check</span>
        <span>Actual</span>
        <span>Allowable</span>
        <span>Margin</span>
        <span>Status</span>
      </div>
      {checks.map((row, i) => (
        <div
          key={row.name}
          className="beam-sct__row"
          style={animate
            ? ({ '--row-delay': `${i * 40}ms` } as React.CSSProperties)
            : undefined}
        >
          <span className="beam-sct__check-name">{checkLabel(row.name)}</span>
          <span className="mono">{fmtSI(row.actual, 'Pa')}</span>
          <span className="mono">{fmtSI(row.allowable, 'Pa')}</span>
          <div className="beam-sct__margin-cell">
            <MarginMeter
              margin={row.margin}
              status={row.status === 'not_modeled' ? 'not_modeled' : row.status}
              animated={animate}
              animationDelay={i * 40}
            />
            <span className="mono beam-sct__margin-pct">
              {row.status === 'not_modeled' ? '—' : `${(row.margin * 100).toFixed(0)}%`}
            </span>
          </div>
          <StatusPill
            status={row.status === 'not_modeled' ? 'not_modeled' : row.status}
            label={row.status === 'not_modeled' ? 'Not modeled' : row.status.charAt(0).toUpperCase() + row.status.slice(1)}
          />
        </div>
      ))}
    </div>
  );
}

// ---- DataTable ----
interface Column {
  key: string;
  label: string;
  mono?: boolean;
  render?: (v: unknown, row: Record<string, unknown>) => React.ReactNode;
}
interface DataTableProps {
  columns: Column[];
  rows: Record<string, unknown>[];
  highlightIndex?: number;
  onRowClick?: (row: Record<string, unknown>, index: number) => void;
}
function DataTable({ columns, rows, highlightIndex, onRowClick }: DataTableProps) {
  return (
    <div className="beam-dt-wrap">
      <table className="beam-dt">
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} className="beam-dt__th">{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className={`beam-dt__row${i === highlightIndex ? ' beam-dt__row--highlight' : ''}`}
              onClick={onRowClick ? () => onRowClick(row, i) : undefined}
              style={onRowClick ? { cursor: 'pointer' } : undefined}
            >
              {columns.map(col => (
                <td key={col.key} className={`beam-dt__td${col.mono ? ' mono' : ''}`}>
                  {col.render
                    ? col.render(row[col.key], row)
                    : String(row[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---- ParetoScatter ----
interface ParetoScatterProps {
  allCandidates: CandidateRow[];
  paretoFront: CandidateRow[];
  kneePoint?: CandidateRow;
  recommended?: CandidateRow;
}

function ParetoScatter({ allCandidates, paretoFront, kneePoint, recommended }: ParetoScatterProps) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; row: CandidateRow } | null>(null);

  const W = 640;
  const H = 320;
  const PAD = { top: 20, right: 24, bottom: 52, left: 60 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const allWeights = allCandidates.map(r => r.weight).filter(isFinite);
  const allCosts   = allCandidates.map(r => r.cost).filter(isFinite);
  if (!allWeights.length || !allCosts.length) return null;

  const minW = Math.min(...allWeights) * 0.9;
  const maxW = Math.max(...allWeights) * 1.05;
  const minC = Math.min(...allCosts) * 0.9;
  const maxC = Math.max(...allCosts) * 1.05;

  function toSvg(weight: number, cost: number): [number, number] {
    const sx = PAD.left + ((weight - minW) / (maxW - minW)) * chartW;
    const sy = PAD.top  + (1 - (cost - minC) / (maxC - minC)) * chartH;
    return [sx, sy];
  }

  // Grid lines
  const xTicks = 5;
  const yTicks = 4;
  const gridLines: React.ReactNode[] = [];
  for (let i = 0; i <= xTicks; i++) {
    const x = PAD.left + (i / xTicks) * chartW;
    const val = minW + (i / xTicks) * (maxW - minW);
    gridLines.push(
      <g key={`xg${i}`}>
        <line x1={x} y1={PAD.top} x2={x} y2={PAD.top + chartH}
          stroke="var(--stroke)" strokeWidth="0.5" />
        <text x={x} y={PAD.top + chartH + 16} textAnchor="middle"
          fontSize="10" fill="var(--text-low)" fontFamily="JetBrains Mono, monospace">
          {val.toFixed(2)}
        </text>
      </g>
    );
  }
  for (let i = 0; i <= yTicks; i++) {
    const y = PAD.top + (i / yTicks) * chartH;
    const val = maxC - (i / yTicks) * (maxC - minC);
    gridLines.push(
      <g key={`yg${i}`}>
        <line x1={PAD.left} y1={y} x2={PAD.left + chartW} y2={y}
          stroke="var(--stroke)" strokeWidth="0.5" />
        <text x={PAD.left - 8} y={y + 4} textAnchor="end"
          fontSize="10" fill="var(--text-low)" fontFamily="JetBrains Mono, monospace">
          {val.toFixed(2)}
        </text>
      </g>
    );
  }

  // Pareto line
  const paretoLine = paretoFront
    .map(r => toSvg(r.weight, r.cost))
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x} ${y}`)
    .join(' ');

  // Recommended coords
  const recCoords = recommended ? toSvg(recommended.weight, recommended.cost) : null;

  return (
    <div className="beam-scatter-wrap">
      <svg
        className="beam-scatter"
        viewBox={`0 0 ${W} ${H}`}
        aria-label="Weight vs Cost Pareto scatter"
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Axes */}
        <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + chartH}
          stroke="var(--stroke)" strokeWidth="1" />
        <line x1={PAD.left} y1={PAD.top + chartH} x2={PAD.left + chartW} y2={PAD.top + chartH}
          stroke="var(--stroke)" strokeWidth="1" />

        {/* Grid */}
        {gridLines}

        {/* Axis labels */}
        <text x={PAD.left + chartW / 2} y={H - 6} textAnchor="middle"
          fontSize="11" fill="var(--text-mid)" fontFamily="Inter, sans-serif">
          Weight (kg)
        </text>
        <text
          x={14} y={PAD.top + chartH / 2} textAnchor="middle"
          fontSize="11" fill="var(--text-mid)" fontFamily="Inter, sans-serif"
          transform={`rotate(-90, 14, ${PAD.top + chartH / 2})`}
        >
          Cost ($)
        </text>

        {/* All candidates (background) */}
        {allCandidates.map((row, i) => {
          const [cx, cy] = toSvg(row.weight, row.cost);
          return (
            <circle
              key={`all-${i}`}
              cx={cx} cy={cy} r={row.safe ? 4 : 3}
              fill={row.safe ? 'var(--text-low)' : 'var(--fail)'}
              opacity={row.safe ? 0.45 : 0.22}
              onMouseEnter={() => setTooltip({ x: cx, y: cy, row })}
            />
          );
        })}

        {/* Pareto front line */}
        {paretoFront.length > 1 && (
          <path d={paretoLine} fill="none" stroke="var(--cyan)" strokeWidth="1.5" opacity="0.7" />
        )}

        {/* Pareto front points */}
        {paretoFront.map((row, i) => {
          const [cx, cy] = toSvg(row.weight, row.cost);
          const isKnee = kneePoint != null && row.weight === kneePoint.weight && row.cost === kneePoint.cost;
          return (
            <circle
              key={`pf-${i}`}
              cx={cx} cy={cy} r={isKnee ? 7 : 5}
              fill={isKnee ? 'var(--accent)' : 'var(--cyan)'}
              stroke={isKnee ? 'var(--accent)' : 'var(--cyan)'}
              strokeWidth={isKnee ? 0 : 1.5}
              opacity={isKnee ? 1 : 0.9}
              className={isKnee ? 'beam-scatter__knee' : undefined}
              onMouseEnter={() => setTooltip({ x: cx, y: cy, row })}
            />
          );
        })}

        {/* Recommended ring */}
        {recCoords && (
          <circle
            cx={recCoords[0]} cy={recCoords[1]} r={9}
            fill="none" stroke="var(--pass)" strokeWidth="2"
          />
        )}

        {/* Tooltip */}
        {tooltip && (() => {
          const tw = 180;
          const th = 80;
          let tx = tooltip.x + 12;
          let ty = tooltip.y - th / 2;
          if (tx + tw > W) tx = tooltip.x - tw - 12;
          if (ty < 0) ty = 4;
          if (ty + th > H) ty = H - th - 4;
          return (
            <g className="beam-scatter__tooltip">
              <rect x={tx} y={ty} width={tw} height={th} rx="6"
                fill="var(--bg-panel)" stroke="var(--stroke)" />
              <text x={tx + 10} y={ty + 18} fontSize="11" fill="var(--text-hi)"
                fontFamily="Inter, sans-serif" fontWeight="600">
                {tooltip.row.material?.replace(/_/g, ' ')}
              </text>
              <text x={tx + 10} y={ty + 34} fontSize="10" fill="var(--text-mid)"
                fontFamily="Inter, sans-serif">
                {tooltip.row.section?.replace(/_/g, ' ')} — {tooltip.row.dims}
              </text>
              <text x={tx + 10} y={ty + 50} fontSize="10" fill="var(--text-low)"
                fontFamily="JetBrains Mono, monospace">
                {`${fmt(tooltip.row.weight, 3)} kg  $${fmt(tooltip.row.cost, 2)}`}
              </text>
              <text x={tx + 10} y={ty + 66} fontSize="10" fill="var(--text-low)"
                fontFamily="JetBrains Mono, monospace">
                {`FoS: ${fmt(tooltip.row.fos, 2)}`}
              </text>
            </g>
          );
        })()}
      </svg>

      {/* Legend */}
      <div className="beam-scatter__legend">
        <span className="beam-scatter__legend-item">
          <span className="beam-scatter__legend-dot" style={{ background: 'var(--text-low)', opacity: 0.45 } as React.CSSProperties} />
          Safe candidate
        </span>
        <span className="beam-scatter__legend-item">
          <span className="beam-scatter__legend-dot" style={{ background: 'var(--fail)', opacity: 0.5 } as React.CSSProperties} />
          Infeasible
        </span>
        <span className="beam-scatter__legend-item">
          <span className="beam-scatter__legend-dot" style={{ background: 'var(--cyan)' } as React.CSSProperties} />
          Pareto front
        </span>
        <span className="beam-scatter__legend-item">
          <span className="beam-scatter__legend-dot" style={{ background: 'var(--accent)' } as React.CSSProperties} />
          Knee point
        </span>
        <span className="beam-scatter__legend-item">
          <span className="beam-scatter__legend-ring" />
          Recommended
        </span>
      </div>
    </div>
  );
}

// ---- Section glyph SVGs ----
function SectionGlyph({ section }: { section: string }) {
  const size = 56;
  const cx = size / 2;
  const cy = size / 2;

  let shape: React.ReactNode;
  switch (section) {
    case 'rectangle':
      shape = <rect x={10} y={16} width={36} height={24} fill="none" stroke="var(--accent)" strokeWidth="2.5" />;
      break;
    case 'circle':
      shape = <circle cx={cx} cy={cy} r={18} fill="none" stroke="var(--accent)" strokeWidth="2.5" />;
      break;
    case 'i_beam':
      shape = (
        <g stroke="var(--accent)" strokeWidth="2.5" fill="none">
          <line x1={12} y1={14} x2={44} y2={14} />
          <line x1={28} y1={14} x2={28} y2={42} />
          <line x1={12} y1={42} x2={44} y2={42} />
        </g>
      );
      break;
    case 'hollow_rectangle':
      shape = (
        <g stroke="var(--accent)" strokeWidth="2.5" fill="none">
          <rect x={10} y={14} width={36} height={28} />
          <rect x={16} y={20} width={24} height={16} />
        </g>
      );
      break;
    case 'square_tube':
      shape = (
        <g stroke="var(--accent)" strokeWidth="2.5" fill="none">
          <rect x={11} y={11} width={34} height={34} />
          <rect x={18} y={18} width={20} height={20} />
        </g>
      );
      break;
    case 'hollow_circle':
      shape = (
        <g stroke="var(--accent)" strokeWidth="2.5" fill="none">
          <circle cx={cx} cy={cy} r={18} />
          <circle cx={cx} cy={cy} r={10} />
        </g>
      );
      break;
    default:
      shape = <rect x={10} y={16} width={36} height={24} fill="none" stroke="var(--accent)" strokeWidth="2.5" />;
  }

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      {shape}
    </svg>
  );
}

// ---- HeroMetric ----
function HeroMetric({ label, value, unit }: { label: string; value: React.ReactNode; unit?: string }) {
  return (
    <div className="beam-hero-metric">
      <span className="beam-hero-metric__label overline">{label}</span>
      <span className="beam-hero-metric__value mono">
        {value}
        {unit && <span className="beam-hero-metric__unit"> {unit}</span>}
      </span>
    </div>
  );
}

// ---- SensitivityBar ----
function SensitivityBar({ row, isMostImportant }: { row: SensitivityRow; isMostImportant: boolean }) {
  const maxFosCh = 2;
  const fosWidth = Math.min(Math.abs(row.fos_change) / maxFosCh, 1) * 100;
  const fosColor = row.fos_change > 0 ? 'var(--pass)' : 'var(--fail)';
  return (
    <div className={`beam-sensitivity-row${isMostImportant ? ' beam-sensitivity-row--highlight' : ''}`}>
      <div className="beam-sensitivity-row__param">
        <span className="label">{row.parameter}</span>
        {isMostImportant && <StatusPill status="warn" label="Most sensitive" />}
      </div>
      <div className="beam-sensitivity-row__bars">
        <div className="beam-sensitivity-row__bar-wrap">
          <span className="overline" style={{ color: 'var(--text-low)' }}>FoS change</span>
          <div className="beam-sensitivity-row__track">
            <div
              className="beam-sensitivity-row__fill"
              style={{
                width: `${fosWidth}%`,
                background: fosColor,
              } as React.CSSProperties}
            />
          </div>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-mid)' }}>
            {row.fos_change > 0 ? '+' : ''}{row.fos_change.toFixed(3)}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────

export default function BeamOptimizer() {
  // ---- Tab
  const [activeTab, setActiveTab] = useState<BeamTab>('setup');

  // ---- Inputs
  const [load, setLoad]         = useState(1000);
  const [length, setLength]     = useState(1.0);
  const [loadCase, setLoadCase] = useState('cantilever_end');
  const [fosTarget, setFosTarget]           = useState(2.0);
  const [deflectionLimit, setDeflectionLimit] = useState(5.0); // in mm for display, converted on submit
  const [priority, setPriority] = useState('balanced');
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>(
    ALL_MATERIALS.map(m => m.id)
  );
  const [selectedSections, setSelectedSections] = useState<string[]>(
    ALL_SECTIONS.map(s => s.id)
  );
  const [stockMode, setStockMode] = useState(false);

  // ---- Results
  const [results, setResults]         = useState<AllResults | null>(null);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError]             = useState<string | null>(null);

  // ---- Run
  const handleRun = useCallback(async () => {
    if (selectedMaterials.length === 0 || selectedSections.length === 0) {
      setError('Select at least one material and one cross-section.');
      return;
    }
    setIsComputing(true);
    setError(null);

    const body = {
      load,
      length,
      load_case: loadCase,
      fos_target: fosTarget,
      deflection_limit: deflectionLimit / 1000, // mm → m
      priority,
      material_keys: selectedMaterials,
      section_types: selectedSections,
      stock_mode: stockMode,
    };

    try {
      const [recommend, rank, pareto, review] = await Promise.all([
        api.beamRecommend(body) as Promise<RecommendResult>,
        api.beamRank(body)       as Promise<RankResult>,
        api.beamPareto(body)     as Promise<ParetoResult>,
        api.beamDesignReview(body) as Promise<ReviewResult>,
      ]);
      setResults({ recommend, rank, pareto, review });
      setActiveTab('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setIsComputing(false);
    }
  }, [load, length, loadCase, fosTarget, deflectionLimit, priority, selectedMaterials, selectedSections, stockMode]);

  // ─── Render helpers ───────────────────────

  function renderGhost(message: string) {
    return (
      <div className="view__placeholder">
        <span className="view__placeholder-icon" aria-hidden="true">◧</span>
        <p>{message}</p>
      </div>
    );
  }

  // ─── Setup Tab ────────────────────────────

  function renderSetup() {
    return (
      <div className="beam-setup">
        {/* Left column: controls */}
        <div className="beam-setup__controls">

          {/* Loading */}
          <Panel title="Loading">
            <div className="beam-controls-row">
              <InputGroup
                label="Load P"
                unit="N"
                value={load}
                onChange={setLoad}
                min={0}
                step={100}
              />
              <InputGroup
                label="Span L"
                unit="m"
                value={length}
                onChange={setLength}
                min={0.01}
                step={0.1}
              />
            </div>

            <p className="overline" style={{ marginTop: 'var(--space-4)', marginBottom: 'var(--space-3)' }}>
              Load Case
            </p>
            <div className="beam-lc-grid">
              {LOAD_CASES.map(lc => (
                <button
                  key={lc.id}
                  type="button"
                  className={`beam-lc-tile${loadCase === lc.id ? ' beam-lc-tile--active' : ''}`}
                  onClick={() => setLoadCase(lc.id)}
                  aria-pressed={loadCase === lc.id}
                >
                  <LoadCaseDiagram id={lc.id} />
                  <span className="beam-lc-tile__label">{lc.label}</span>
                  <span className="beam-lc-tile__desc">{lc.description}</span>
                </button>
              ))}
            </div>
          </Panel>

          {/* Constraints */}
          <Panel title="Constraints">
            <div className="beam-controls-row">
              <InputGroup
                label="Target FoS"
                value={fosTarget}
                onChange={setFosTarget}
                min={1.0}
                step={0.1}
                helperText="Minimum factor of safety"
              />
              <InputGroup
                label="Max Deflection"
                unit="mm"
                value={deflectionLimit}
                onChange={setDeflectionLimit}
                min={0.1}
                step={0.5}
                helperText="Upper bound on tip deflection"
              />
            </div>
          </Panel>

          {/* Priority */}
          <Panel title="Priority">
            <SegmentedToggle
              options={PRIORITY_OPTIONS}
              value={priority}
              onChange={setPriority}
              label="Optimization objective"
            />
          </Panel>

          {/* Materials */}
          <Panel title="Materials">
            <ChipSelector
              chips={ALL_MATERIALS}
              selected={selectedMaterials}
              onChange={setSelectedMaterials}
              label="Active materials"
            />
          </Panel>

          {/* Cross-Sections */}
          <Panel title="Cross-Sections">
            <ChipSelector
              chips={ALL_SECTIONS}
              selected={selectedSections}
              onChange={setSelectedSections}
              label="Active cross-sections"
            />
          </Panel>

          {/* Design Mode */}
          <Panel title="Design Mode">
            <SegmentedToggle
              options={[
                { value: 'false', label: 'Conceptual Sweep' },
                { value: 'true',  label: 'Standard Stock' },
              ]}
              value={stockMode ? 'true' : 'false'}
              onChange={v => setStockMode(v === 'true')}
              label="Dimension source"
            />
          </Panel>

          {/* Error */}
          {error && (
            <div className="beam-error" role="alert">
              <span className="beam-error__icon" aria-hidden="true">!</span>
              <span className="beam-error__msg">{error}</span>
            </div>
          )}

          {/* Run button */}
          <button
            className={`beam-run-btn${isComputing ? ' beam-run-btn--loading' : ''}`}
            onClick={handleRun}
            disabled={isComputing}
            type="button"
          >
            {isComputing ? (
              <>
                <span className="beam-run-btn__spinner" aria-hidden="true" />
                Computing…
              </>
            ) : 'Run Optimizer'}
          </button>
        </div>

        {/* Right column: beam preview */}
        <div className="beam-setup__preview">
          <Panel title="Beam Preview">
            <BeamPreviewSVG loadCase={loadCase} load={load} length={length} />
            <div className="beam-preview-meta">
              <span className="overline">Load case</span>
              <span className="label" style={{ color: 'var(--text-hi)' }}>
                {LOAD_CASES.find(lc => lc.id === loadCase)?.label}
              </span>
            </div>
          </Panel>
        </div>
      </div>
    );
  }

  // ─── Results Tab ──────────────────────────

  function renderResults() {
    if (!results) {
      return renderGhost('Run the optimizer from Setup to see results.');
    }

    const rec = results.recommend.recommended;
    const rank = results.rank;
    const overallStatus = statusToPanel(rec.safety_case?.overall_status ?? 'neutral');
    const safeCount = rank.ranked.filter(r => r.safe).length;
    const matSet  = new Set(rank.ranked.map(r => r.material));
    const secSet  = new Set(rank.ranked.map(r => r.section));

    return (
      <div className="beam-results">
        {/* Hero card */}
        <div className={`beam-hero beam-hero--${overallStatus}`}>
          <div className="beam-hero__strip" />
          <div className="beam-hero__glyph">
            <SectionGlyph section={rec.section} />
          </div>
          <div className="beam-hero__center">
            <p className="overline">Recommended Design</p>
            <h2 className="beam-hero__name">
              {rec.material?.replace(/_/g, ' ')} / {rec.section?.replace(/_/g, ' ')} / {rec.dims}
            </h2>
            <div className="beam-hero__metrics">
              <HeroMetric
                label="Factor of Safety"
                value={<span style={{ fontSize: 26, color: 'var(--pass)' }}>{fmt(rec.fos, 2)}</span>}
              />
              <HeroMetric label="Weight"     value={fmt(rec.weight, 3)}     unit="kg" />
              <HeroMetric label="Cost"       value={`$${fmt(rec.cost, 2)}`} />
              <HeroMetric label="Stress"     value={fmtSI(rec.stress, 'Pa')} />
              <HeroMetric label="Deflection" value={fmtSI(rec.deflection, 'm')} />
            </div>
            {results.review?.why_it_won && (
              <p className="beam-hero__why">{results.review.why_it_won}</p>
            )}
          </div>
          <div className="beam-hero__status-badge">
            <StatusPill
              status={overallStatus === 'pass' ? 'pass' : overallStatus === 'fail' ? 'fail' : 'warn'}
              label={rec.safety_case?.overall_status?.toUpperCase() ?? 'UNKNOWN'}
            />
          </div>
        </div>

        {/* Safety case table */}
        <Panel title="Safety Case Checks">
          {rec.safety_case?.checks ? (
            <SafetyCaseTable checks={rec.safety_case.checks} animate />
          ) : (
            <p className="label" style={{ color: 'var(--text-low)' }}>No safety case data returned.</p>
          )}
        </Panel>

        {/* Candidates summary */}
        <Panel title="Sweep Summary">
          <div className="beam-summary-row">
            <div className="beam-summary-stat">
              <span className="beam-summary-stat__val mono">{rank.ranked.length}</span>
              <span className="beam-summary-stat__label overline">Candidates evaluated</span>
            </div>
            <div className="beam-summary-stat">
              <span className="beam-summary-stat__val mono" style={{ color: 'var(--pass)' }}>{safeCount}</span>
              <span className="beam-summary-stat__label overline">Safe designs</span>
            </div>
            <div className="beam-summary-stat">
              <span className="beam-summary-stat__val mono">{matSet.size}</span>
              <span className="beam-summary-stat__label overline">Materials</span>
            </div>
            <div className="beam-summary-stat">
              <span className="beam-summary-stat__val mono">{secSet.size}</span>
              <span className="beam-summary-stat__label overline">Section types</span>
            </div>
          </div>
        </Panel>
      </div>
    );
  }

  // ─── Tradeoffs Tab ────────────────────────

  function renderTradeoffs() {
    if (!results) {
      return renderGhost('Run the optimizer from Setup to see tradeoff charts.');
    }

    const ranked = results.rank.ranked;
    const pareto = results.pareto;
    const topFive = ranked.slice(0, 5);

    const rankColumns: Column[] = [
      { key: 'rank',     label: 'Rank',    mono: true },
      { key: 'material', label: 'Material', render: v => String(v).replace(/_/g, ' ') },
      { key: 'section',  label: 'Section',  render: v => String(v).replace(/_/g, ' ') },
      { key: 'dims',     label: 'Dims',     mono: true },
      { key: 'weight',   label: 'Weight (kg)', mono: true, render: v => fmt(v as number, 3) },
      { key: 'cost',     label: 'Cost ($)',    mono: true, render: v => `$${fmt(v as number, 2)}` },
      { key: 'fos',      label: 'FoS',         mono: true, render: v => fmt(v as number, 2) },
      {
        key: 'safe', label: 'Status',
        render: (v) => (
          <StatusPill
            status={v ? 'pass' : 'fail'}
            label={v ? 'Safe' : 'Fail'}
          />
        ),
      },
    ];

    return (
      <div className="beam-tradeoffs">
        {/* Pareto scatter */}
        <Panel title="Pareto Front — Weight vs Cost">
          <ParetoScatter
            allCandidates={ranked}
            paretoFront={pareto.front}
            kneePoint={pareto.knee_point}
            recommended={results.recommend.recommended}
          />
        </Panel>

        {/* Top-5 table */}
        <Panel title="Top-5 Ranked Candidates">
          <DataTable
            columns={rankColumns}
            rows={topFive as unknown as Record<string, unknown>[]}
            highlightIndex={0}
          />
        </Panel>

        {/* Envelope note */}
        <Panel title="Load-Case Envelope">
          <p className="label" style={{ color: 'var(--text-low)', lineHeight: 1.6 }}>
            Load-case envelope analysis computes worst-case stress and deflection across all
            active load cases simultaneously. To run an envelope sweep, configure multiple
            load magnitudes in Setup and re-run.
          </p>
        </Panel>
      </div>
    );
  }

  // ─── Design Review Tab ────────────────────

  function renderDesignReview() {
    if (!results) {
      return renderGhost('Run the optimizer from Setup to see the design review.');
    }

    const review = results.review;
    if (!review) {
      return renderGhost('Design review data unavailable.');
    }

    const sections = [
      {
        id: 'recommended',
        label: 'Recommended Design',
        content: (
          <p className="label" style={{ color: 'var(--text-hi)', fontSize: 15, lineHeight: 1.7 }}>
            {typeof review.recommended === 'object' && review.recommended
              ? `${String(review.recommended.material ?? '').replace(/_/g, ' ')} / ${String(review.recommended.section ?? '').replace(/_/g, ' ')} / ${review.recommended.dims ?? ''}`
              : String(review.recommended)}
          </p>
        ),
      },
      {
        id: 'why',
        label: 'Why It Won',
        content: (
          <p className="label" style={{ color: 'var(--text-mid)', lineHeight: 1.7 }}>
            {review.why_it_won}
          </p>
        ),
      },
      {
        id: 'controlling',
        label: 'Controlling Constraint',
        content: (
          <div className="beam-review-constraint">
            <span className="label" style={{ color: 'var(--text-hi)' }}>
              {checkLabel(review.controlling_constraint)}
            </span>
            <div className="beam-review-constraint__meter">
              <MarginMeter
                margin={review.controlling_margin}
                status={review.controlling_margin < 0.1 ? 'fail' : review.controlling_margin < 0.3 ? 'warn' : 'pass'}
                animated
              />
              <span className="mono" style={{ fontSize: 12, color: 'var(--text-mid)' }}>
                {(review.controlling_margin * 100).toFixed(0)}% margin
              </span>
            </div>
          </div>
        ),
      },
      {
        id: 'sensitivity',
        label: 'Sensitivity Analysis',
        content: (
          <div className="beam-review-sensitivities">
            {review.sensitivities?.length ? (
              review.sensitivities.map(s => (
                <SensitivityBar
                  key={s.parameter}
                  row={s}
                  isMostImportant={s.parameter === review.most_important_sensitivity}
                />
              ))
            ) : (
              <p className="label" style={{ color: 'var(--text-low)' }}>
                No sensitivity data returned.
              </p>
            )}
          </div>
        ),
      },
      {
        id: 'risks',
        label: 'Unmodeled Risks',
        content: (
          <div className="beam-review-risks">
            {review.unmodeled_risks?.length ? (
              review.unmodeled_risks.map(risk => (
                <StatusPill key={risk} status="warn" label={checkLabel(risk)} />
              ))
            ) : (
              <StatusPill status="pass" label="No unmodeled risks flagged" />
            )}
          </div>
        ),
      },
      {
        id: 'alternative',
        label: 'Nearest Alternative',
        content: (
          <p className="label" style={{ color: 'var(--text-mid)', lineHeight: 1.6 }}>
            {review.nearest_alternative || 'No alternative available.'}
          </p>
        ),
      },
      {
        id: 'next',
        label: 'Recommended Next Step',
        content: (
          <p className="label" style={{ color: 'var(--cyan)', lineHeight: 1.6 }}>
            {review.recommended_next_step || '—'}
          </p>
        ),
      },
    ];

    return (
      <Panel title="Design Review Report">
        <div className="beam-review-doc">
          {sections.map((sec, i) => (
            <div
              key={sec.id}
              className="beam-review-section"
              style={{ '--section-delay': `${i * 80}ms` } as React.CSSProperties}
            >
              <span className="overline beam-review-section__overline">{sec.label}</span>
              <div className="beam-review-section__body">{sec.content}</div>
            </div>
          ))}
        </div>
      </Panel>
    );
  }

  // ─── Load case SVG diagrams (tiny) ────────

  function LoadCaseDiagram({ id }: { id: string }) {
    const w = 64, h = 32;
    switch (id) {
      case 'cantilever_end':
        return (
          <svg viewBox={`0 0 ${w} ${h}`} className="beam-lc-diagram" aria-hidden="true">
            <rect x={0} y={10} width={8} height={12} fill="var(--stroke)" />
            <line x1={8} y1={16} x2={56} y2={16} stroke="var(--text-mid)" strokeWidth="3" />
            <line x1={52} y1={6} x2={52} y2={16} stroke="var(--accent)" strokeWidth="1.5" />
            <polygon points="52,16 49,10 55,10" fill="var(--accent)" />
          </svg>
        );
      case 'cantilever_udl':
        return (
          <svg viewBox={`0 0 ${w} ${h}`} className="beam-lc-diagram" aria-hidden="true">
            <rect x={0} y={10} width={8} height={12} fill="var(--stroke)" />
            <line x1={8} y1={16} x2={56} y2={16} stroke="var(--text-mid)" strokeWidth="3" />
            {[16, 24, 32, 40, 48].map(x => (
              <g key={x}>
                <line x1={x} y1={6} x2={x} y2={14} stroke="var(--accent)" strokeWidth="1.5" />
                <polygon points={`${x},14 ${x - 2.5},9 ${x + 2.5},9`} fill="var(--accent)" />
              </g>
            ))}
            <line x1={8} y1={6} x2={56} y2={6} stroke="var(--accent)" strokeWidth="1" />
          </svg>
        );
      case 'simply_center':
        return (
          <svg viewBox={`0 0 ${w} ${h}`} className="beam-lc-diagram" aria-hidden="true">
            <line x1={8} y1={16} x2={56} y2={16} stroke="var(--text-mid)" strokeWidth="3" />
            <polygon points="8,16 4,24 12,24"  fill="none" stroke="var(--stroke)" strokeWidth="1.5" />
            <polygon points="56,16 52,24 60,24" fill="none" stroke="var(--stroke)" strokeWidth="1.5" />
            <line x1={32} y1={4} x2={32} y2={14} stroke="var(--accent)" strokeWidth="1.5" />
            <polygon points="32,14 29,8 35,8" fill="var(--accent)" />
          </svg>
        );
      case 'simply_udl':
        return (
          <svg viewBox={`0 0 ${w} ${h}`} className="beam-lc-diagram" aria-hidden="true">
            <line x1={8} y1={16} x2={56} y2={16} stroke="var(--text-mid)" strokeWidth="3" />
            <polygon points="8,16 4,24 12,24"  fill="none" stroke="var(--stroke)" strokeWidth="1.5" />
            <polygon points="56,16 52,24 60,24" fill="none" stroke="var(--stroke)" strokeWidth="1.5" />
            {[14, 22, 30, 38, 46, 54].map(x => (
              <g key={x}>
                <line x1={x} y1={6} x2={x} y2={14} stroke="var(--accent)" strokeWidth="1.5" />
                <polygon points={`${x},14 ${x - 2.5},9 ${x + 2.5},9`} fill="var(--accent)" />
              </g>
            ))}
            <line x1={8} y1={6} x2={56} y2={6} stroke="var(--accent)" strokeWidth="1" />
          </svg>
        );
      default:
        return null;
    }
  }

  // ─── Root render ──────────────────────────

  return (
    <div className="view">
      <div className="view__header">
        <p className="overline">Structural Analysis</p>
        <h1 className="view__title">Beam Optimizer</h1>
        <p className="view__subtitle">
          Sweep materials, cross-sections, and dimensions. Find the lightest, cheapest,
          or safest design under your load case.
        </p>
      </div>

      <div className="view__subtabs" role="tablist" aria-label="Beam optimizer tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`beam-panel-${tab.id}`}
            className={`view__subtab${activeTab === tab.id ? ' view__subtab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.id !== 'setup' && !results && (
              <span className="beam-tab-dot" aria-hidden="true" />
            )}
          </button>
        ))}
      </div>

      <div
        id={`beam-panel-${activeTab}`}
        role="tabpanel"
        aria-label={TABS.find(t => t.id === activeTab)?.label}
        className="view__tab-content"
        key={activeTab}
      >
        {activeTab === 'setup'         && renderSetup()}
        {activeTab === 'results'       && renderResults()}
        {activeTab === 'tradeoffs'     && renderTradeoffs()}
        {activeTab === 'design-review' && renderDesignReview()}
      </div>
    </div>
  );
}

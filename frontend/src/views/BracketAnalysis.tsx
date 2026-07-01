/**
 * BracketAnalysis.tsx
 * Full Bracket Analysis view — Setup, Plate & Bolts, Gusset, Warnings.
 * The animated bracket SVG is the centrepiece of the Setup tab.
 */

import { useState, useCallback } from 'react';
import Panel from '../components/Panel';
import StatusPill from '../components/StatusPill';
import MarginMeter from '../components/MarginMeter';
import InputGroup from '../components/InputGroup';
import SegmentedToggle from '../components/SegmentedToggle';
import { api } from '../api';
import './View.css';
import './BracketAnalysis.css';

// ─── Types ──────────────────────────────────────────────────────────────────

type BracketTab = 'setup' | 'plate-bolts' | 'gusset' | 'warnings';

type GussetType = 'none' | 'flat_L' | 'triangular' | 'double_gusset' | 'ribbed';

interface BoltResult {
  shear_per_bolt: number;
  max_tension: number;
  bolt_area: number;
  shear_stress: number;
  tension_stress: number;
  combined_utilization: number;
  bolt_fos: number;
  bearing_stress: number;
  bearing_fos: number;
  tearout_stress: number;
  tearout_fos: number;
  edge_distance_ok: boolean;
  warnings: string[];
}

interface GussetResult {
  gusset_type: string;
  depth: number;
  thickness: number;
  mass: number;
}

interface EvaluateResult {
  plate_stress: number;
  plate_deflection: number;
  plate_fos: number;
  plate_mass: number;
  total_mass: number;
  bolt: BoltResult;
  overall_fos: number;
  safe: boolean;
  controlling: string;
  gusset: GussetResult | null;
}

interface GussetCompareRow extends EvaluateResult {
  // Same shape as EvaluateResult
}

interface GussetCompareResult {
  results: GussetCompareRow[];
}

// ─── Constants ───────────────────────────────────────────────────────────────

const TABS: { id: BracketTab; label: string }[] = [
  { id: 'setup',       label: 'Setup' },
  { id: 'plate-bolts', label: 'Plate & Bolts' },
  { id: 'gusset',      label: 'Gusset' },
  { id: 'warnings',    label: 'Warnings' },
];

const MATERIAL_OPTIONS = [
  { id: 'steel_a36',        label: 'Steel A36' },
  { id: 'aluminum_6061',    label: 'Alum 6061' },
  { id: 'pla',              label: 'PLA' },
  { id: 'titanium_ti6al4v', label: 'Ti-6Al-4V' },
  { id: 'brass_360',        label: 'Brass 360' },
  { id: 'abs_plastic',      label: 'ABS' },
];

const GUSSET_OPTIONS: { id: GussetType; label: string }[] = [
  { id: 'none',          label: 'None' },
  { id: 'flat_L',        label: 'Flat L' },
  { id: 'triangular',    label: 'Triangular' },
  { id: 'double_gusset', label: 'Double' },
  { id: 'ribbed',        label: 'Ribbed' },
];

const GUSSET_COMPARE_TYPES: GussetType[] = [
  'none', 'flat_L', 'triangular', 'double_gusset', 'ribbed',
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fosBadge(fos: number, target: number): 'pass' | 'warn' | 'fail' {
  if (fos >= target) return 'pass';
  if (fos >= target * 0.9) return 'warn';
  return 'fail';
}

function fosMargin(fos: number, target: number): number {
  // Margin = (FoS - target) / target, clamped to [-1, 1]
  return Math.max(-1, Math.min(1, (fos - target) / target));
}

function fmtN(v: number, dp = 1): string {
  return v.toFixed(dp);
}

function fmtPct(v: number): string {
  return (v * 100).toFixed(1) + '%';
}

function controllingLabel(k: string): string {
  const map: Record<string, string> = {
    plate_bending: 'Plate Bending',
    bolt:          'Bolt Group',
    deflection:    'Tip Deflection',
  };
  return map[k] ?? k;
}

// ─── Bracket SVG ─────────────────────────────────────────────────────────────

interface BracketSVGProps {
  P: number;
  e: number;         // mm
  width: number;     // mm  (plate width = height in side view)
  thickness: number; // mm  (plate thickness)
  boltCount: number;
  boltDiameter: number;    // mm
  boltSpacingV: number;    // mm
  gussetType: GussetType;
  gussetDepth: number;     // mm
}

function BracketSVG({
  P,
  e,
  width,
  thickness,
  boltCount,
  boltDiameter,
  boltSpacingV,
  gussetType,
  gussetDepth,
}: BracketSVGProps) {
  // Layout constants (SVG canvas 520 × 320)
  const W = 520;
  const H = 320;
  const wallX = 90;    // x position of wall face
  const wallThick = 28;
  const midY = H / 2;

  // Scale: fit offset e into available horizontal space
  const maxDrawE = W - wallX - 60;
  const scale = Math.min(maxDrawE / Math.max(e, 10), 3.5); // px/mm

  const armLength = e * scale;            // horizontal extent of arm
  const armThick  = Math.max(6, Math.min(thickness * scale * 1.2, 28));
  const armHeight = Math.max(20, Math.min(width * scale * 0.35, 60));

  const armLeft  = wallX;
  const armRight = wallX + armLength;
  const armTop   = midY - armThick / 2;
  const armBot   = midY + armThick / 2;

  // Bolt group
  const boltR    = Math.max(3, Math.min(boltDiameter * scale * 0.6, 9));
  const boltSpY  = Math.max(12, Math.min(boltSpacingV * scale * 0.6, 36));
  const boltX    = wallX + Math.max(boltR + 4, 16);
  const totalBoltSpan = (boltCount - 1) * boltSpY;
  const boltTopY = midY - totalBoltSpan / 2;
  const bolts: { cx: number; cy: number }[] = [];
  for (let i = 0; i < boltCount; i++) {
    bolts.push({ cx: boltX, cy: boltTopY + i * boltSpY });
  }

  // Load arrow
  const arrowX   = armRight;
  const arrowLen = Math.max(28, Math.min(P / 10, 60));
  const arrowTop = armBot;

  // Gusset geometry
  const gDepth = Math.max(10, Math.min(gussetDepth * scale * 0.5, armLength * 0.75));

  function renderGusset() {
    if (gussetType === 'none') return null;

    const wallFace = wallX;
    const gY1 = armBot;   // base of arm at wall
    const gY2 = midY + armHeight * 0.5 + 12; // gusset bottom at wall

    if (gussetType === 'flat_L') {
      // L-shaped: horizontal plate along bottom of arm + vertical leg at wall
      const horizW = gDepth;
      const vertH  = 10;
      return (
        <g className="bracket-svg__gusset" aria-label="Flat L gusset">
          {/* Horizontal plate below arm */}
          <rect
            x={wallFace}
            y={armBot}
            width={horizW}
            height={vertH}
            fill="rgba(34,211,238,0.18)"
            stroke="var(--cyan)"
            strokeWidth="1.5"
            rx="2"
          />
          {/* Vertical leg at wall */}
          <rect
            x={wallFace}
            y={armBot}
            width={8}
            height={vertH + 14}
            fill="rgba(34,211,238,0.12)"
            stroke="var(--cyan)"
            strokeWidth="1.5"
            rx="2"
          />
        </g>
      );
    }

    if (gussetType === 'triangular') {
      const pts = [
        `${wallFace},${gY1}`,
        `${wallFace + gDepth},${armBot}`,
        `${wallFace},${gY2}`,
      ].join(' ');
      return (
        <polygon
          className="bracket-svg__gusset"
          points={pts}
          fill="rgba(34,211,238,0.15)"
          stroke="var(--cyan)"
          strokeWidth="1.5"
          aria-label="Triangular gusset"
        />
      );
    }

    if (gussetType === 'double_gusset') {
      const ptsBot = [
        `${wallFace},${gY1}`,
        `${wallFace + gDepth},${armBot}`,
        `${wallFace},${gY2}`,
      ].join(' ');
      const gY1t = armTop;
      const gY2t = midY - armHeight * 0.5 - 12;
      const ptsTop = [
        `${wallFace},${gY1t}`,
        `${wallFace + gDepth},${armTop}`,
        `${wallFace},${gY2t}`,
      ].join(' ');
      return (
        <g className="bracket-svg__gusset" aria-label="Double gusset">
          <polygon
            points={ptsBot}
            fill="rgba(34,211,238,0.15)"
            stroke="var(--cyan)"
            strokeWidth="1.5"
          />
          <polygon
            points={ptsTop}
            fill="rgba(34,211,238,0.15)"
            stroke="var(--cyan)"
            strokeWidth="1.5"
          />
        </g>
      );
    }

    if (gussetType === 'ribbed') {
      const pts = [
        `${wallFace},${gY1}`,
        `${wallFace + gDepth},${armBot}`,
        `${wallFace},${gY2}`,
      ].join(' ');
      // Internal ribs: lines from the hypotenuse inward
      const ribCount = 3;
      const ribs: React.ReactNode[] = [];
      for (let i = 1; i <= ribCount; i++) {
        const t = i / (ribCount + 1);
        const rx1 = wallFace + gDepth * t;
        const ry1 = armBot;
        const rx2 = wallFace;
        const ry2 = gY1 + (gY2 - gY1) * t;
        ribs.push(
          <line
            key={i}
            x1={rx1} y1={ry1}
            x2={rx2} y2={ry2}
            stroke="var(--cyan)"
            strokeWidth="0.8"
            opacity="0.5"
          />
        );
      }
      return (
        <g className="bracket-svg__gusset" aria-label="Ribbed gusset">
          <polygon
            points={pts}
            fill="rgba(34,211,238,0.15)"
            stroke="var(--cyan)"
            strokeWidth="1.5"
          />
          {ribs}
        </g>
      );
    }

    return null;
  }

  // Dimension line helpers
  function dimLine(
    x1: number, y1: number,
    x2: number, y2: number,
    label: string,
    offsetDir: 'up' | 'down' | 'left' | 'right' = 'down',
  ) {
    const off = 14;
    let lx = (x1 + x2) / 2;
    let ly = (y1 + y2) / 2;
    if (offsetDir === 'down') ly += off;
    if (offsetDir === 'up')   ly -= off;
    if (offsetDir === 'left') lx -= off;
    if (offsetDir === 'right') lx += off;

    return (
      <g className="bracket-svg__dim" opacity="0.55">
        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--text-low)" strokeWidth="0.8" strokeDasharray="4 3" />
        <line x1={x1} y1={y1 - 4} x2={x1} y2={y1 + 4} stroke="var(--text-low)" strokeWidth="0.8" />
        <line x1={x2} y1={y2 - 4} x2={x2} y2={y2 + 4} stroke="var(--text-low)" strokeWidth="0.8" />
        <text
          x={lx} y={ly}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="var(--text-low)"
          fontSize="9"
          fontFamily="JetBrains Mono, monospace"
        >
          {label}
        </text>
      </g>
    );
  }

  // Hatch pattern for wall
  const hatchId = 'bracket-wall-hatch';

  return (
    <svg
      className="bracket-svg"
      viewBox={`0 0 ${W} ${H}`}
      aria-label="Animated bracket diagram"
      role="img"
    >
      <defs>
        <pattern
          id={hatchId}
          width="8"
          height="8"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="8" stroke="var(--stroke)" strokeWidth="3" />
        </pattern>

        {/* Glow filter for load arrow */}
        <filter id="bracket-arrow-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Glow filter for bolts */}
        <filter id="bracket-bolt-glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* ── Grid lines — subtle dashed horizontals ── */}
      {Array.from({ length: Math.floor(H / 50) }, (_, i) => (
        <line key={`grid-${i}`} x1={0} y1={i * 50} x2={W} y2={i * 50}
          stroke="var(--stroke-soft)" strokeWidth="0.5" strokeDasharray="4 6" opacity="0.3" />
      ))}

      {/* ── Title label ── */}
      <text x={14} y={18} fontSize="9" fill="var(--text-low)"
        fontFamily="Inter, sans-serif" fontWeight="600" letterSpacing="2" opacity="0.7">
        BRACKET — BOLT GROUP + GUSSET
      </text>

      {/* ── Wall ── */}
      <rect
        x={wallX - wallThick}
        y={0}
        width={wallThick}
        height={H}
        fill={`url(#${hatchId})`}
        className="bracket-svg__wall-fill"
      />
      {/* Wall face line */}
      <line
        x1={wallX} y1={0}
        x2={wallX} y2={H}
        stroke="var(--text-mid)"
        strokeWidth="2.5"
        className="bracket-svg__wall-face"
      />

      {/* ── Gusset (behind arm) ── */}
      {renderGusset()}

      {/* ── Arm / Plate ── */}
      <rect
        x={armLeft}
        y={armTop}
        width={armLength}
        height={armThick}
        fill="rgba(154,164,184,0.18)"
        stroke="var(--text-mid)"
        strokeWidth="1.8"
        rx="2"
        className="bracket-svg__arm"
      />

      {/* ── Bolt group ── */}
      {bolts.map((b, i) => (
        <g key={i} filter="url(#bracket-bolt-glow)">
          <circle
            cx={b.cx}
            cy={b.cy}
            r={boltR + 2}
            fill="rgba(59,130,246,0.10)"
            stroke="var(--accent)"
            strokeWidth="0.6"
          />
          <circle
            cx={b.cx}
            cy={b.cy}
            r={boltR}
            fill="rgba(59,130,246,0.25)"
            stroke="var(--accent)"
            strokeWidth="1.4"
            className="bracket-svg__bolt"
          />
          {/* Bolt head cross */}
          <line
            x1={b.cx - boltR * 0.55} y1={b.cy}
            x2={b.cx + boltR * 0.55} y2={b.cy}
            stroke="var(--accent)"
            strokeWidth="0.8"
            opacity="0.7"
          />
          <line
            x1={b.cx} y1={b.cy - boltR * 0.55}
            x2={b.cx} y2={b.cy + boltR * 0.55}
            stroke="var(--accent)"
            strokeWidth="0.8"
            opacity="0.7"
          />
        </g>
      ))}

      {/* ── Load arrow ── */}
      <g filter="url(#bracket-arrow-glow)" className="bracket-svg__load-arrow">
        <line
          x1={arrowX}
          y1={arrowTop}
          x2={arrowX}
          y2={arrowTop + arrowLen}
          stroke="var(--fail)"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        {/* Arrow head */}
        <polygon
          points={[
            `${arrowX},${arrowTop + arrowLen + 8}`,
            `${arrowX - 6},${arrowTop + arrowLen}`,
            `${arrowX + 6},${arrowTop + arrowLen}`,
          ].join(' ')}
          fill="var(--fail)"
        />
        {/* Load label */}
        <text
          x={arrowX + 10}
          y={arrowTop + arrowLen / 2}
          fill="var(--fail)"
          fontSize="10"
          fontFamily="JetBrains Mono, monospace"
          dominantBaseline="middle"
          opacity="0.85"
        >
          P={P} N
        </text>
      </g>

      {/* ── Dimension: offset e ── */}
      {dimLine(wallX, armBot + 22, armRight, armBot + 22, `e=${e} mm`, 'down')}

      {/* ── Dimension: bolt spacing ── */}
      {boltCount > 1 && dimLine(
        boltX + boltR + 4, boltTopY,
        boltX + boltR + 4, boltTopY + totalBoltSpan,
        `s=${boltSpacingV}`,
        'right',
      )}

      {/* ── Dimension: plate thickness ── */}
      {dimLine(
        wallX - 36, armTop,
        wallX - 36, armBot,
        `t=${thickness}`,
        'left',
      )}

      {/* ── Labels ── */}
      <text
        x={wallX - wallThick / 2}
        y={H - 10}
        textAnchor="middle"
        fill="var(--text-low)"
        fontSize="9"
        fontFamily="Inter, sans-serif"
        opacity="0.6"
      >
        WALL
      </text>
      {gussetType !== 'none' && (
        <text
          x={wallX + gDepth * 0.4}
          y={midY + armThick / 2 + 28}
          textAnchor="middle"
          fill="var(--cyan)"
          fontSize="9"
          fontFamily="Inter, sans-serif"
          opacity="0.75"
        >
          {GUSSET_OPTIONS.find(g => g.id === gussetType)?.label ?? ''}
        </text>
      )}

      {/* ── Legend ── */}
      <g transform={`translate(14, ${H - 22})`}>
        {[
          { label: 'Plate', color: 'var(--text-mid)' },
          { label: 'Bolts', color: 'var(--accent)' },
          { label: 'Gusset', color: 'var(--cyan)' },
          { label: 'Load', color: 'var(--fail)' },
        ].map((item, i) => (
          <g key={item.label} transform={`translate(${i * 80}, 0)`}>
            <circle cx={4} cy={5} r={4} fill={item.color} />
            <text x={14} y={9} fontSize="9" fill="var(--text-mid)"
              fontFamily="Inter, sans-serif">{item.label}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}

// ─── Gusset Tile SVG diagrams ─────────────────────────────────────────────────

function GussetDiagramSVG({ type }: { type: GussetType }) {
  const W = 64;
  const H = 48;
  const wallX = 14;
  const armY = H / 2;
  const armLen = 44;
  const armThick = 7;

  const commonArm = (
    <>
      <line x1={wallX} y1={0} x2={wallX} y2={H} stroke="var(--text-low)" strokeWidth="2" />
      <rect
        x={wallX}
        y={armY - armThick / 2}
        width={armLen}
        height={armThick}
        fill="rgba(154,164,184,0.2)"
        stroke="var(--text-mid)"
        strokeWidth="1.2"
        rx="1"
      />
    </>
  );

  const gussetColor = 'rgba(34,211,238,0.6)';
  const gussetStroke = 'var(--cyan)';

  if (type === 'none') {
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="bracket-gusset-diag">
        {commonArm}
      </svg>
    );
  }

  if (type === 'flat_L') {
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="bracket-gusset-diag">
        {commonArm}
        <rect x={wallX} y={armY + armThick / 2} width={22} height={6}
          fill={gussetColor} stroke={gussetStroke} strokeWidth="1" rx="1" />
        <rect x={wallX} y={armY + armThick / 2} width={5} height={14}
          fill={gussetColor} stroke={gussetStroke} strokeWidth="1" rx="1" />
      </svg>
    );
  }

  if (type === 'triangular') {
    const pts = [
      `${wallX},${armY + armThick / 2}`,
      `${wallX + 28},${armY + armThick / 2}`,
      `${wallX},${armY + armThick / 2 + 20}`,
    ].join(' ');
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="bracket-gusset-diag">
        {commonArm}
        <polygon points={pts} fill={gussetColor} stroke={gussetStroke} strokeWidth="1" />
      </svg>
    );
  }

  if (type === 'double_gusset') {
    const ptsBot = [
      `${wallX},${armY + armThick / 2}`,
      `${wallX + 28},${armY + armThick / 2}`,
      `${wallX},${armY + armThick / 2 + 18}`,
    ].join(' ');
    const ptsTop = [
      `${wallX},${armY - armThick / 2}`,
      `${wallX + 28},${armY - armThick / 2}`,
      `${wallX},${armY - armThick / 2 - 18}`,
    ].join(' ');
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="bracket-gusset-diag">
        {commonArm}
        <polygon points={ptsBot} fill={gussetColor} stroke={gussetStroke} strokeWidth="1" />
        <polygon points={ptsTop} fill={gussetColor} stroke={gussetStroke} strokeWidth="1" />
      </svg>
    );
  }

  if (type === 'ribbed') {
    const pts = [
      `${wallX},${armY + armThick / 2}`,
      `${wallX + 28},${armY + armThick / 2}`,
      `${wallX},${armY + armThick / 2 + 20}`,
    ].join(' ');
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="bracket-gusset-diag">
        {commonArm}
        <polygon points={pts} fill={gussetColor} stroke={gussetStroke} strokeWidth="1" />
        {[1, 2].map(i => {
          const t = i / 3;
          return (
            <line
              key={i}
              x1={wallX + 28 * t} y1={armY + armThick / 2}
              x2={wallX}          y2={armY + armThick / 2 + 20 * t}
              stroke={gussetStroke}
              strokeWidth="0.7"
              opacity="0.65"
            />
          );
        })}
      </svg>
    );
  }

  return null;
}

// ─── Metric block ─────────────────────────────────────────────────────────────

function Metric({
  label,
  value,
  unit,
  large,
  accent,
}: {
  label: string;
  value: string;
  unit?: string;
  large?: boolean;
  accent?: string;
}) {
  return (
    <div className="bracket-metric">
      <span className="overline bracket-metric__label">{label}</span>
      <span
        className={`bracket-metric__value ${large ? 'bracket-metric__value--large' : ''}`}
        style={accent ? { color: accent } : undefined}
      >
        {value}
        {unit && <span className="bracket-metric__unit"> {unit}</span>}
      </span>
    </div>
  );
}

// ─── Delta chip ──────────────────────────────────────────────────────────────

function DeltaChip({ value, good }: { value: string; good: boolean }) {
  return (
    <span className={`bracket-delta ${good ? 'bracket-delta--good' : 'bracket-delta--bad'}`}>
      {value}
    </span>
  );
}

// ─── Warning card ─────────────────────────────────────────────────────────────

function WarningCard({
  title,
  body,
  pillStatus,
  pillLabel,
}: {
  title: string;
  body: string;
  pillStatus: 'warn' | 'not_modeled';
  pillLabel: string;
}) {
  return (
    <Panel status="warn">
      <div className="bracket-warn-card">
        <div className="bracket-warn-card__header">
          <span className="bracket-warn-card__title">{title}</span>
          <StatusPill status={pillStatus} label={pillLabel} />
        </div>
        <p className="bracket-warn-card__body">{body}</p>
      </div>
    </Panel>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function BracketAnalysis() {
  // Sub-tab
  const [activeTab, setActiveTab] = useState<BracketTab>('setup');

  // ── Inputs ──
  const [P,              setP]              = useState(500);
  const [e,              setE]              = useState(100);
  const [width,          setWidth]          = useState(40);
  const [thickness,      setThickness]      = useState(8);
  const [materialKey,    setMaterialKey]    = useState('steel_a36');
  const [fosTarget,      setFosTarget]      = useState(2.0);
  const [deflectionLimit, setDeflectionLimit] = useState(5.0);
  const [boltCount,      setBoltCount]      = useState(4);
  const [boltDiameter,   setBoltDiameter]   = useState(8);
  const [boltSpacingV,   setBoltSpacingV]   = useState(40);
  const [boltSigmaAllow, setBoltSigmaAllow] = useState(640);
  const [edgeDistance,   setEdgeDistance]   = useState(16);
  const [gussetType,     setGussetType]     = useState<GussetType>('none');
  const [gussetDepth,    setGussetDepth]    = useState(50);
  const [gussetThickness, setGussetThickness] = useState(8);

  // ── Results ──
  const [result,           setResult]           = useState<EvaluateResult | null>(null);
  const [gussetComparison, setGussetComparison] = useState<GussetCompareResult | null>(null);
  const [isComputing,      setIsComputing]      = useState(false);
  const [error,            setError]            = useState<string | null>(null);

  // ─── Run analysis ──────────────────────────────────────────────────────────

  const handleRun = useCallback(async () => {
    setIsComputing(true);
    setError(null);

    const body = {
      P,
      e:               e / 1000,
      width:           width / 1000,
      thickness:       thickness / 1000,
      material_key:    materialKey,
      fos_target:      fosTarget,
      bolt_count:      boltCount,
      bolt_diameter:   boltDiameter / 1000,
      bolt_spacing_v:  boltSpacingV / 1000,
      bolt_sigma_allow: boltSigmaAllow * 1e6,
      deflection_limit: deflectionLimit / 1000,
      gusset_type:     gussetType,
      gusset_depth:    gussetDepth / 1000,
      gusset_thickness: gussetThickness / 1000,
      edge_distance:   edgeDistance / 1000,
    };

    try {
      const [evalResult, compareResult] = await Promise.all([
        api.bracketEvaluate(body) as Promise<EvaluateResult>,
        api.bracketCompareGussets(body) as Promise<GussetCompareResult>,
      ]);
      setResult(evalResult);
      setGussetComparison(compareResult);
      setActiveTab('plate-bolts');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed — check backend connection.');
    } finally {
      setIsComputing(false);
    }
  }, [
    P, e, width, thickness, materialKey, fosTarget, deflectionLimit,
    boltCount, boltDiameter, boltSpacingV, boltSigmaAllow, edgeDistance,
    gussetType, gussetDepth, gussetThickness,
  ]);

  // ─── Derived ───────────────────────────────────────────────────────────────

  const overallStatus = result
    ? fosBadge(result.overall_fos, fosTarget)
    : 'neutral';

  const plateBadge = result
    ? fosBadge(result.plate_fos, fosTarget)
    : 'neutral';

  const boltBadge = result
    ? fosBadge(result.bolt.bolt_fos, fosTarget)
    : 'neutral';

  // ─── Tab helpers ───────────────────────────────────────────────────────────

  function tabLabel(tab: BracketTab): string {
    const base = TABS.find(t => t.id === tab)?.label ?? tab;
    if (tab !== 'setup' && !result) return base;
    return base;
  }

  // ─── Gusset comparison table ───────────────────────────────────────────────

  function renderGussetTable() {
    if (!gussetComparison || !result) return null;
    const rows = gussetComparison.results;
    if (!rows || rows.length === 0) return null;

    const noneRow = rows[0]; // first row = none

    return (
      <div className="bracket-gcomp-wrap">
        <table className="bracket-gcomp">
          <thead>
            <tr className="bracket-gcomp__head">
              <th className="bracket-gcomp__th">Type</th>
              <th className="bracket-gcomp__th">Deflection (mm)</th>
              <th className="bracket-gcomp__th">Δ Defl</th>
              <th className="bracket-gcomp__th">FoS</th>
              <th className="bracket-gcomp__th">Δ FoS</th>
              <th className="bracket-gcomp__th">Added Mass (g)</th>
              <th className="bracket-gcomp__th">Controlling</th>
              <th className="bracket-gcomp__th">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const typeName = GUSSET_OPTIONS[idx]?.label ?? `Type ${idx}`;
              const typeId   = GUSSET_COMPARE_TYPES[idx] ?? 'none';
              const isCurrent = typeId === gussetType;

              const deflMm    = row.plate_deflection * 1000;
              const noneDefl  = noneRow.plate_deflection * 1000;
              const deltaDefl = idx === 0 ? 0 : ((deflMm - noneDefl) / noneDefl) * 100;
              const deltaFos  = idx === 0 ? 0 : row.overall_fos - noneRow.overall_fos;
              const addedMassG = idx === 0
                ? 0
                : ((row.total_mass - noneRow.total_mass) * 1000);

              const deflGood = deltaDefl <= 0;
              const fosGood  = deltaFos  >= 0;

              return (
                <tr
                  key={idx}
                  className={[
                    'bracket-gcomp__row',
                    isCurrent ? 'bracket-gcomp__row--current' : '',
                    row.safe ? '' : 'bracket-gcomp__row--unsafe',
                  ].filter(Boolean).join(' ')}
                >
                  <td className="bracket-gcomp__td bracket-gcomp__td--name">
                    {isCurrent && <span className="bracket-gcomp__cur-dot" aria-hidden="true" />}
                    {typeName}
                  </td>
                  <td className="bracket-gcomp__td bracket-gcomp__td--mono">
                    {deflMm.toFixed(3)}
                  </td>
                  <td className="bracket-gcomp__td">
                    {idx === 0
                      ? <span className="bracket-gcomp__td--dim">—</span>
                      : <DeltaChip
                          value={`${deltaDefl > 0 ? '+' : ''}${deltaDefl.toFixed(1)}%`}
                          good={deflGood}
                        />
                    }
                  </td>
                  <td className="bracket-gcomp__td bracket-gcomp__td--mono">
                    {row.overall_fos.toFixed(2)}
                  </td>
                  <td className="bracket-gcomp__td">
                    {idx === 0
                      ? <span className="bracket-gcomp__td--dim">—</span>
                      : <DeltaChip
                          value={`${deltaFos >= 0 ? '+' : ''}${deltaFos.toFixed(2)}`}
                          good={fosGood}
                        />
                    }
                  </td>
                  <td className="bracket-gcomp__td bracket-gcomp__td--mono">
                    {idx === 0 ? '—' : `+${addedMassG.toFixed(1)}`}
                  </td>
                  <td className="bracket-gcomp__td bracket-gcomp__td--dim">
                    {controllingLabel(row.controlling)}
                  </td>
                  <td className="bracket-gcomp__td">
                    <StatusPill
                      status={row.safe ? 'pass' : 'fail'}
                      label={row.safe ? 'Safe' : 'Unsafe'}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  // ─── Before / after hero ──────────────────────────────────────────────────

  function renderBeforeAfterHero() {
    if (!gussetComparison || gussetType === 'none') return null;
    const rows = gussetComparison.results;
    if (!rows || rows.length < 2) return null;

    const noneRow    = rows[0];
    const activeIdx  = GUSSET_COMPARE_TYPES.indexOf(gussetType);
    const activeRow  = activeIdx >= 0 ? rows[activeIdx] : null;
    if (!activeRow) return null;

    const noneDefl   = noneRow.plate_deflection * 1000;
    const activeDefl = activeRow.plate_deflection * 1000;
    const deflChange = ((activeDefl - noneDefl) / noneDefl) * 100;
    const fosChange  = activeRow.overall_fos - noneRow.overall_fos;
    const massAdd    = (activeRow.total_mass - noneRow.total_mass) * 1000;

    const gLabel = GUSSET_OPTIONS.find(g => g.id === gussetType)?.label ?? gussetType;

    return (
      <Panel className="bracket-before-after">
        <div className="bracket-ba">
          <div className="bracket-ba__side">
            <span className="overline">No Gusset</span>
            <span className="bracket-ba__val">{noneDefl.toFixed(3)} mm</span>
            <span className="bracket-ba__sub">deflection</span>
            <span className="bracket-ba__val">{noneRow.overall_fos.toFixed(2)}</span>
            <span className="bracket-ba__sub">FoS</span>
            <StatusPill status={noneRow.safe ? 'pass' : 'fail'} label={noneRow.safe ? 'Safe' : 'Unsafe'} />
          </div>

          <div className="bracket-ba__arrow" aria-hidden="true">
            <svg viewBox="0 0 40 24" width="40" height="24">
              <line x1="4" y1="12" x2="30" y2="12" stroke="var(--text-low)" strokeWidth="1.5" />
              <polygon points="36,12 28,8 28,16" fill="var(--text-low)" />
            </svg>
            <span className="bracket-ba__arrow-label">{gLabel}</span>
          </div>

          <div className="bracket-ba__side">
            <span className="overline">{gLabel} Gusset</span>
            <span className="bracket-ba__val">{activeDefl.toFixed(3)} mm</span>
            <span className="bracket-ba__sub">deflection</span>
            <span className="bracket-ba__val">{activeRow.overall_fos.toFixed(2)}</span>
            <span className="bracket-ba__sub">FoS</span>
            <StatusPill status={activeRow.safe ? 'pass' : 'fail'} label={activeRow.safe ? 'Safe' : 'Unsafe'} />
          </div>

          <div className="bracket-ba__deltas">
            <div className="bracket-ba__delta-row">
              <span className="bracket-ba__delta-label">Deflection</span>
              <DeltaChip
                value={`${deflChange > 0 ? '+' : ''}${deflChange.toFixed(1)}%`}
                good={deflChange <= 0}
              />
            </div>
            <div className="bracket-ba__delta-row">
              <span className="bracket-ba__delta-label">FoS</span>
              <DeltaChip
                value={`${fosChange >= 0 ? '+' : ''}${fosChange.toFixed(2)}`}
                good={fosChange >= 0}
              />
            </div>
            <div className="bracket-ba__delta-row">
              <span className="bracket-ba__delta-label">Added Mass</span>
              <DeltaChip
                value={`+${massAdd.toFixed(1)} g`}
                good={false}
              />
            </div>
            <div className="bracket-ba__delta-row">
              <span className="bracket-ba__delta-label">Control shifts</span>
              <span className="bracket-ba__delta-label">
                {controllingLabel(noneRow.controlling)} → {controllingLabel(activeRow.controlling)}
              </span>
            </div>
          </div>
        </div>
      </Panel>
    );
  }

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="view">
      <div className="view__header">
        <p className="overline">Structural Analysis</p>
        <h1 className="view__title">Bracket Analysis</h1>
        <p className="view__subtitle">
          Wall-mounted bracket — plate bending, bolt group shear and tension,
          gusset comparison, and controlling-constraint identification.
        </p>
      </div>

      {/* Sub-tab selector */}
      <div className="view__subtabs" role="tablist" aria-label="Bracket analysis tabs">
        {TABS.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`bracket-panel-${tab.id}`}
            className={`view__subtab ${activeTab === tab.id ? 'view__subtab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tabLabel(tab.id)}
            {tab.id !== 'setup' && tab.id !== 'warnings' && !result && (
              <span className="bracket-tab-lock" aria-label="Run analysis to unlock" />
            )}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      <div
        id={`bracket-panel-${activeTab}`}
        role="tabpanel"
        aria-label={TABS.find(t => t.id === activeTab)?.label}
        className="view__tab-content"
        key={activeTab}
      >

        {/* ══════════════════════════════════════════════
            SETUP TAB
        ══════════════════════════════════════════════ */}
        {activeTab === 'setup' && (
          <div className="bracket-setup">

            {/* ── Left: control cards ── */}
            <div className="bracket-setup__controls">

              {/* ── Plate / Arm ── */}
              <Panel title="Plate / Arm">
                <div className="bracket-field-stack">
                  <div className="bracket-row-2">
                    <InputGroup
                      label="Load P"
                      unit="N"
                      value={P}
                      onChange={v => setP(Number(v))}
                      type="number"
                      min={1}
                      step={10}
                    />
                    <InputGroup
                      label="Offset e"
                      unit="mm"
                      value={e}
                      onChange={v => setE(Number(v))}
                      type="number"
                      min={10}
                      step={10}
                      helperText="Distance from wall to load point"
                    />
                  </div>
                  <div className="bracket-row-2">
                    <InputGroup
                      label="Width"
                      unit="mm"
                      value={width}
                      onChange={v => setWidth(Number(v))}
                      type="number"
                      min={10}
                      step={5}
                    />
                    <InputGroup
                      label="Thickness"
                      unit="mm"
                      value={thickness}
                      onChange={v => setThickness(Number(v))}
                      type="number"
                      min={2}
                      step={1}
                    />
                  </div>

                  {/* Material */}
                  <div className="bracket-field">
                    <span className="overline bracket-field__label">Material</span>
                    <SegmentedToggle
                      options={MATERIAL_OPTIONS}
                      value={materialKey}
                      onChange={setMaterialKey}
                    />
                  </div>

                  <div className="bracket-row-2">
                    <InputGroup
                      label="Target FoS"
                      value={fosTarget}
                      onChange={v => setFosTarget(Number(v))}
                      type="number"
                      min={1}
                      step={0.1}
                    />
                    <InputGroup
                      label="Max Deflection"
                      unit="mm"
                      value={deflectionLimit}
                      onChange={v => setDeflectionLimit(Number(v))}
                      type="number"
                      min={0.1}
                      step={0.5}
                    />
                  </div>
                </div>
              </Panel>

              {/* ── Bolt Group ── */}
              <Panel title="Bolt Group">
                <div className="bracket-field-stack">
                  <div className="bracket-row-2">
                    <InputGroup
                      label="Bolt Count"
                      value={boltCount}
                      onChange={v => setBoltCount(Math.max(2, Math.min(8, Number(v))))}
                      type="number"
                      min={2}
                      max={8}
                      step={1}
                    />
                    <InputGroup
                      label="Bolt Diameter"
                      unit="mm"
                      value={boltDiameter}
                      onChange={v => setBoltDiameter(Number(v))}
                      type="number"
                      min={4}
                      step={1}
                    />
                  </div>
                  <div className="bracket-row-2">
                    <InputGroup
                      label="Vertical Spacing"
                      unit="mm"
                      value={boltSpacingV}
                      onChange={v => setBoltSpacingV(Number(v))}
                      type="number"
                      min={10}
                      step={5}
                    />
                    <InputGroup
                      label="Allowable Stress"
                      unit="MPa"
                      value={boltSigmaAllow}
                      onChange={v => setBoltSigmaAllow(Number(v))}
                      type="number"
                      min={100}
                      step={10}
                    />
                  </div>
                  <InputGroup
                    label="Edge Distance"
                    unit="mm"
                    value={edgeDistance}
                    onChange={v => setEdgeDistance(Number(v))}
                    type="number"
                    min={4}
                    step={1}
                    helperText={`Min recommended: ${(boltDiameter * 2).toFixed(0)} mm (2× bolt diameter)`}
                  />
                </div>
              </Panel>

              {/* ── Gusset selector ── */}
              <Panel title="Gusset">
                <div className="bracket-gusset-grid">
                  {GUSSET_OPTIONS.map(opt => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setGussetType(opt.id)}
                      className={[
                        'bracket-gusset-tile',
                        gussetType === opt.id ? 'bracket-gusset-tile--active' : '',
                      ].join(' ')}
                      aria-pressed={gussetType === opt.id}
                      aria-label={`Gusset type: ${opt.label}`}
                    >
                      <GussetDiagramSVG type={opt.id} />
                      <span className="bracket-gusset-tile__label">{opt.label}</span>
                    </button>
                  ))}
                </div>

                {gussetType !== 'none' && (
                  <div className="bracket-gusset-params">
                    <div className="bracket-row-2">
                      <InputGroup
                        label="Gusset Depth"
                        unit="mm"
                        value={gussetDepth}
                        onChange={v => setGussetDepth(Number(v))}
                        type="number"
                        min={10}
                        step={5}
                      />
                      <InputGroup
                        label="Gusset Thickness"
                        unit="mm"
                        value={gussetThickness}
                        onChange={v => setGussetThickness(Number(v))}
                        type="number"
                        min={2}
                        step={1}
                      />
                    </div>
                  </div>
                )}
              </Panel>

              {/* ── Error ── */}
              {error && (
                <div className="bracket-error" role="alert">
                  <span className="bracket-error__icon" aria-hidden="true">!</span>
                  <p className="bracket-error__msg">{error}</p>
                </div>
              )}

              {/* ── Run button ── */}
              <button
                type="button"
                className={`bracket-run-btn ${isComputing ? 'bracket-run-btn--loading' : ''}`}
                onClick={handleRun}
                disabled={isComputing}
                aria-busy={isComputing}
              >
                {isComputing && (
                  <span className="bracket-run-btn__spinner" aria-hidden="true" />
                )}
                {isComputing ? 'Analyzing…' : 'Analyze Bracket'}
              </button>
            </div>

            {/* ── Right: SVG preview ── */}
            <div className="bracket-setup__preview">
              <Panel className="bracket-svg-panel">
                <BracketSVG
                  P={P}
                  e={e}
                  width={width}
                  thickness={thickness}
                  boltCount={boltCount}
                  boltDiameter={boltDiameter}
                  boltSpacingV={boltSpacingV}
                  gussetType={gussetType}
                  gussetDepth={gussetDepth}
                />
                <div className="bracket-svg-legend">
                  <span className="bracket-svg-legend__item">
                    <span className="bracket-svg-legend__dot bracket-svg-legend__dot--plate" />
                    Plate
                  </span>
                  <span className="bracket-svg-legend__item">
                    <span className="bracket-svg-legend__dot bracket-svg-legend__dot--bolt" />
                    Bolts
                  </span>
                  {gussetType !== 'none' && (
                    <span className="bracket-svg-legend__item">
                      <span className="bracket-svg-legend__dot bracket-svg-legend__dot--gusset" />
                      Gusset
                    </span>
                  )}
                  <span className="bracket-svg-legend__item">
                    <span className="bracket-svg-legend__dot bracket-svg-legend__dot--load" />
                    Load
                  </span>
                </div>
              </Panel>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════
            PLATE & BOLTS TAB
        ══════════════════════════════════════════════ */}
        {activeTab === 'plate-bolts' && (
          <div className="bracket-results">
            {!result ? (
              <div className="view__placeholder">
                <span className="view__placeholder-icon" aria-hidden="true">⟁</span>
                <p>Run the analysis in the Setup tab to see plate bending and bolt group results.</p>
              </div>
            ) : (
              <>
                {/* Three result cards */}
                <div className="view__grid view__grid--3">

                  {/* Plate card */}
                  <Panel title="Plate Bending" status={plateBadge}>
                    <div className="bracket-field-stack">
                      <Metric
                        label="Bending Stress σ_b"
                        value={fmtN(result.plate_stress / 1e6, 2)}
                        unit="MPa"
                      />
                      <Metric
                        label="Plate FoS"
                        value={result.plate_fos.toFixed(2)}
                        large
                        accent={plateBadge === 'pass' ? 'var(--pass)' : plateBadge === 'warn' ? 'var(--warn)' : 'var(--fail)'}
                      />
                      <Metric
                        label="Tip Deflection"
                        value={fmtN(result.plate_deflection * 1000, 3)}
                        unit="mm"
                      />
                      <Metric
                        label="Plate Mass"
                        value={fmtN(result.plate_mass * 1000, 1)}
                        unit="g"
                      />
                      <MarginMeter
                        margin={fosMargin(result.plate_fos, fosTarget)}
                        status={plateBadge}
                        animated
                      />
                    </div>
                  </Panel>

                  {/* Bolt group card */}
                  <Panel title="Bolt Group" status={boltBadge}>
                    <div className="bracket-field-stack">
                      <Metric
                        label="Shear / Bolt"
                        value={fmtN(result.bolt.shear_per_bolt, 1)}
                        unit="N"
                      />
                      <Metric
                        label="Max Tension"
                        value={fmtN(result.bolt.max_tension, 1)}
                        unit="N"
                      />
                      <Metric
                        label="Combined Utilization"
                        value={fmtPct(result.bolt.combined_utilization)}
                      />
                      <Metric
                        label="Bolt FoS"
                        value={result.bolt.bolt_fos.toFixed(2)}
                        large
                        accent={boltBadge === 'pass' ? 'var(--pass)' : boltBadge === 'warn' ? 'var(--warn)' : 'var(--fail)'}
                      />
                      <MarginMeter
                        margin={fosMargin(result.bolt.bolt_fos, fosTarget)}
                        status={boltBadge}
                        animated
                        animationDelay={100}
                      />
                    </div>
                  </Panel>

                  {/* Bearing & tear-out card */}
                  <Panel title="Bearing & Tear-out">
                    <div className="bracket-field-stack">
                      <Metric
                        label="Bearing Stress"
                        value={fmtN(result.bolt.bearing_stress / 1e6, 2)}
                        unit="MPa"
                      />
                      <Metric
                        label="Bearing FoS"
                        value={result.bolt.bearing_fos.toFixed(1)}
                      />
                      <Metric
                        label="Tearout Stress"
                        value={fmtN(result.bolt.tearout_stress / 1e6, 2)}
                        unit="MPa"
                      />
                      <Metric
                        label="Tearout FoS"
                        value={result.bolt.tearout_fos.toFixed(1)}
                      />
                      <div className="bracket-field-row">
                        <span className="overline bracket-field__label">Edge Distance</span>
                        <StatusPill
                          status={result.bolt.edge_distance_ok ? 'pass' : 'fail'}
                          label={result.bolt.edge_distance_ok ? 'OK' : 'Too Small'}
                        />
                      </div>
                      {result.bolt.warnings.length > 0 && (
                        <div className="bracket-bolt-warnings">
                          {result.bolt.warnings.map((w, i) => (
                            <span key={i} className="bracket-bolt-warn-chip">{w}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </Panel>
                </div>

                {/* Overall FoS hero */}
                <div className={`bracket-overall-hero bracket-overall-hero--${overallStatus}`}>
                  <span className="bracket-overall-hero__strip" aria-hidden="true" />
                  <div className="bracket-overall-hero__body">
                    <div className="bracket-overall-hero__left">
                      <span className="overline">Overall Factor of Safety</span>
                      <span className="bracket-overall-hero__fos">
                        {result.overall_fos.toFixed(2)}
                      </span>
                      <span className="bracket-overall-hero__controlling">
                        Controlled by <strong>{controllingLabel(result.controlling)}</strong>
                      </span>
                    </div>
                    <div className="bracket-overall-hero__right">
                      <StatusPill
                        status={result.safe ? 'pass' : 'fail'}
                        label={result.safe ? 'SAFE' : 'UNSAFE'}
                      />
                      <MarginMeter
                        margin={fosMargin(result.overall_fos, fosTarget)}
                        status={overallStatus}
                        animated
                        animationDelay={200}
                      />
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════
            GUSSET TAB
        ══════════════════════════════════════════════ */}
        {activeTab === 'gusset' && (
          <div className="bracket-results">
            {!gussetComparison ? (
              <div className="view__placeholder">
                <span className="view__placeholder-icon" aria-hidden="true">⟁</span>
                <p>Run the analysis in the Setup tab to compare gusset types.</p>
              </div>
            ) : (
              <>
                <Panel title="Gusset Type Comparison">
                  {renderGussetTable()}
                </Panel>

                {gussetType !== 'none' && renderBeforeAfterHero()}
              </>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════
            WARNINGS TAB
        ══════════════════════════════════════════════ */}
        {activeTab === 'warnings' && (
          <div className="bracket-results">
            <div className="bracket-warn-list">

              <WarningCard
                title="Wall Substrate"
                body="This analysis assumes a rigid wall attachment. Actual bracket performance depends on the wall substrate (concrete, wood stud, steel column). Substrate stiffness is not modeled and can significantly affect deflection and load distribution."
                pillStatus="not_modeled"
                pillLabel="Not Modeled"
              />

              <WarningCard
                title="Wall Anchorage"
                body="Does not check wall anchorage — anchor bolt pull-out, concrete cone failure, and stud fastener capacity are outside this model's scope. Consult the relevant anchor standard (e.g. ACI 318 Appendix D, ETAG 001) for anchor design."
                pillStatus="not_modeled"
                pillLabel="Not Modeled"
              />

              <WarningCard
                title="Unmodeled Effects"
                body="Fatigue, corrosion, dynamic loading, thermal effects, and weld quality are not considered. In real installations all four should be evaluated, particularly if loads are cyclic or the environment is corrosive."
                pillStatus="warn"
                pillLabel="Warning"
              />

              {/* Any bolt.warnings from the last analysis */}
              {result && result.bolt.warnings.length > 0 && (
                <>
                  {result.bolt.warnings.map((w, i) => (
                    <Panel key={i} status="warn">
                      <div className="bracket-warn-card">
                        <div className="bracket-warn-card__header">
                          <span className="bracket-warn-card__title">Bolt Group Warning</span>
                          <StatusPill status="warn" label="Warning" />
                        </div>
                        <p className="bracket-warn-card__body">{w}</p>
                      </div>
                    </Panel>
                  ))}
                </>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

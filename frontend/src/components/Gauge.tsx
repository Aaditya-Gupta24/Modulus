import { useEffect, useRef, useState } from 'react';
import './Gauge.css';

interface Zone {
  from: number;
  to: number;
  color: string;
}

interface GaugeProps {
  value: number;
  min?: number;
  max?: number;
  label: string;
  zones?: Zone[];
  animate?: boolean;
}

// Default zones for FoS reading
const DEFAULT_ZONES: Zone[] = [
  { from: 0, to: 1,   color: 'var(--fail)' },
  { from: 1, to: 2,   color: 'var(--warn)' },
  { from: 2, to: 10,  color: 'var(--pass)' },
];

// SVG arc helpers
// The gauge sweeps 240 degrees clockwise: from 210deg (bottom-left) to 90deg
// (bottom-right, i.e. 210 + 240 = 450 mod 360 = 90).
// This is a classic ¾-circle gauge. 0deg is 3 o'clock in SVG coordinates.
const START_DEG = 210;
const TOTAL_DEG = 240; // total clockwise sweep in degrees

const CX = 60;   // center x
const CY = 56;   // center y (shifted up slightly so text clears the bottom)
const R  = 44;   // arc radius
const NEEDLE_R = 38; // needle length from center

function degToRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

function polarToXY(deg: number, r: number): { x: number; y: number } {
  const rad = degToRad(deg);
  return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

// Returns the absolute angle (from SVG 0=3 o'clock, clockwise) for a value
function valueToAbsDeg(v: number, min: number, max: number): number {
  const t = clamp((v - min) / (max - min), 0, 1);
  return START_DEG + t * TOTAL_DEG;
}

// Build an SVG arc from fromDeg to toDeg (clockwise, sweepDeg degrees)
function arcPath(fromDeg: number, sweepDeg: number, r: number): string {
  const start    = polarToXY(fromDeg, r);
  const end      = polarToXY(fromDeg + sweepDeg, r);
  const largeArc = sweepDeg > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

function formatValue(v: number): string {
  if (!isFinite(v)) return '—';
  if (Math.abs(v) >= 100) return v.toFixed(0);
  if (Math.abs(v) >= 10)  return v.toFixed(1);
  return v.toFixed(2);
}

export default function Gauge({
  value,
  min = 0,
  max = 10,
  label,
  zones = DEFAULT_ZONES,
  animate = true,
}: GaugeProps) {
  const [displayedDeg, setDisplayedDeg] = useState<number>(START_DEG);
  const rafRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const startDegRef  = useRef<number>(START_DEG);

  const targetDeg = valueToAbsDeg(value, min, max);

  // Smooth needle animation using requestAnimationFrame
  useEffect(() => {
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!animate || prefersReduced) {
      setDisplayedDeg(targetDeg);
      return;
    }

    const duration = 420; // ms, matches --dur-slow
    startDegRef.current = displayedDeg;
    startTimeRef.current = null;

    function easeInOut(t: number): number {
      // cubic ease-in-out matching --ease-io
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function tick(now: number) {
      if (startTimeRef.current === null) startTimeRef.current = now;
      const elapsed = now - startTimeRef.current;
      const t = Math.min(elapsed / duration, 1);
      const eased = easeInOut(t);
      const current = startDegRef.current + (targetDeg - startDegRef.current) * eased;
      setDisplayedDeg(current);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
    // We intentionally exclude displayedDeg from deps to avoid restarting mid-animation
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetDeg, animate]);

  // Needle tip
  const needleTip = polarToXY(displayedDeg, NEEDLE_R);
  const needleBase1 = polarToXY(displayedDeg + 90, 4);
  const needleBase2 = polarToXY(displayedDeg - 90, 4);

  // Track arc starts at START_DEG and sweeps TOTAL_DEG clockwise
  const trackFrom = START_DEG;

  return (
    <div className="gauge" role="meter" aria-valuenow={value} aria-valuemin={min} aria-valuemax={max} aria-label={label}>
      <svg
        className="gauge__svg"
        viewBox="0 0 120 90"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        focusable="false"
      >
        {/* Track (full sweep background) */}
        <path
          className="gauge__track"
          d={arcPath(trackFrom, TOTAL_DEG, R)}
          fill="none"
          stroke="var(--stroke)"
          strokeWidth="5"
          strokeLinecap="round"
        />

        {/* Zone arcs */}
        {zones.map((zone, i) => {
          const zFrom = clamp(zone.from, min, max);
          const zTo   = clamp(zone.to,   min, max);
          if (zFrom >= zTo) return null;
          const dFrom   = valueToAbsDeg(zFrom, min, max);
          const dTo     = valueToAbsDeg(zTo,   min, max);
          const dSweep  = dTo - dFrom; // always positive since zFrom < zTo
          return (
            <path
              key={i}
              d={arcPath(dFrom, dSweep, R)}
              fill="none"
              stroke={zone.color}
              strokeWidth="5"
              strokeLinecap="round"
              opacity="0.55"
            />
          );
        })}

        {/* Needle */}
        <polygon
          className="gauge__needle"
          points={`${needleTip.x},${needleTip.y} ${needleBase1.x},${needleBase1.y} ${needleBase2.x},${needleBase2.y}`}
          fill="var(--text-mid)"
        />

        {/* Center pivot */}
        <circle cx={CX} cy={CY} r="4" className="gauge__pivot" />
        <circle cx={CX} cy={CY} r="2" fill="var(--bg-panel)" />

        {/* Value text */}
        <text
          x={CX}
          y={CY - 10}
          textAnchor="middle"
          className="gauge__value-text"
          dominantBaseline="auto"
        >
          {formatValue(value)}
        </text>

        {/* Label text */}
        <text
          x={CX}
          y={CY + 2}
          textAnchor="middle"
          className="gauge__label-text"
          dominantBaseline="hanging"
        >
          {label}
        </text>
      </svg>
    </div>
  );
}

import { useEffect, useRef } from 'react';
import './ReactiveField.css';

/**
 * ReactiveField — a cursor-reactive FEA stress-field heatmap on a technical grid.
 * The pointer probes the field: nodes near the cursor heat up (dark -> maroon ->
 * red -> hot orange). Slow ambient waves keep it alive when idle.
 *
 * Robust by design:
 *  - ResizeObserver keeps the canvas buffer matched to its box (survives async
 *    layout growth, e.g. the materials table loading).
 *  - Pointer is converted to canvas-local coords against the LIVE rect each frame,
 *    so heat tracks the cursor correctly even while the page scrolls.
 *  - Respects prefers-reduced-motion (one static frame, no tracking).
 */

interface ReactiveFieldProps {
  className?: string;
  spacing?: number;
  radius?: number;
}

const STOPS: [number, number, number, number][] = [
  [0.0, 18, 14, 20],
  [0.45, 80, 24, 32],
  [0.72, 160, 36, 46],
  [0.9, 222, 54, 62],
  [1.0, 248, 98, 74],
];

function sample(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t));
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [a, ar, ag, ab] = STOPS[i];
    const [b, br, bg, bb] = STOPS[i + 1];
    if (x >= a && x <= b) {
      const k = (x - a) / (b - a || 1);
      return [ar + (br - ar) * k, ag + (bg - ag) * k, ab + (bb - ab) * k];
    }
  }
  const last = STOPS[STOPS.length - 1];
  return [last[1], last[2], last[3]];
}

export default function ReactiveField({
  className = '',
  spacing = 44,
  radius = 240,
}: ReactiveFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    const cv = canvas;
    const g = context;

    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let w = 0;
    let h = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    const ptr = { x: -9999, y: -9999, active: false };
    const smooth = { x: -9999, y: -9999 };

    function resize() {
      const rect = cv.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      cv.width = Math.max(1, Math.floor(w * dpr));
      cv.height = Math.max(1, Math.floor(h * dpr));
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function onMove(e: PointerEvent) {
      ptr.x = e.clientX;
      ptr.y = e.clientY;
      ptr.active = true;
    }
    function onLeave() {
      ptr.active = false;
    }

    const r2 = radius * radius;

    function draw(time: number) {
      const rect = cv.getBoundingClientRect();
      const tx = ptr.active ? ptr.x - rect.left : -9999;
      const ty = ptr.active ? ptr.y - rect.top : -9999;

      if (tx < -9000) {
        smooth.x = -9999;
        smooth.y = -9999;
      } else if (smooth.x < -9000) {
        smooth.x = tx;
        smooth.y = ty;
      } else {
        smooth.x += (tx - smooth.x) * 0.14;
        smooth.y += (ty - smooth.y) * 0.14;
      }

      g.clearRect(0, 0, w, h);

      const t = time * 0.0003;
      const cell = Math.max(2, spacing - 26);

      for (let gy = spacing / 2; gy < h; gy += spacing) {
        for (let gx = spacing / 2; gx < w; gx += spacing) {
          const ambient =
            0.06 +
            0.03 *
              (Math.sin(gx * 0.012 + t) * 0.5 + Math.sin(gy * 0.015 - t * 1.3) * 0.5);

          let heat = 0;
          if (smooth.x > -9000) {
            const dx = gx - smooth.x;
            const dy = gy - smooth.y;
            const d2 = dx * dx + dy * dy;
            if (d2 < r2) {
              const f = 1 - d2 / r2;
              heat = f * f;
            }
          }

          const energy = Math.min(1, ambient + heat);
          const [r, gCol, b] = sample(energy);
          const alpha = 0.06 + energy * 0.6 + heat * 0.2;
          const size = cell + heat * 4;
          g.fillStyle = `rgba(${r | 0},${gCol | 0},${b | 0},${alpha.toFixed(3)})`;
          g.fillRect(gx - size / 2, gy - size / 2, size, size);
        }
      }
    }

    resize();
    window.addEventListener('resize', resize);

    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => resize());
      ro.observe(cv);
    }

    if (reduced) {
      draw(0);
      return () => {
        window.removeEventListener('resize', resize);
        ro?.disconnect();
      };
    }

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerleave', onLeave);

    let raf = 0;
    let last = 0;
    const loop = (ts: number) => {
      if (ts - last > 24) {
        draw(ts);
        last = ts;
      }
      raf = requestAnimationFrame(loop);
    };

    function onVisibility() {
      if (document.hidden) {
        cancelAnimationFrame(raf);
      } else {
        raf = requestAnimationFrame(loop);
      }
    }
    document.addEventListener('visibilitychange', onVisibility);
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerleave', onLeave);
      document.removeEventListener('visibilitychange', onVisibility);
      ro?.disconnect();
    };
  }, [spacing, radius]);

  return (
    <canvas
      ref={canvasRef}
      className={`reactive-field ${className}`}
      aria-hidden="true"
    />
  );
}

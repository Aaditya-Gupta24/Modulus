import { useEffect, useRef } from 'react';
import './ReactiveField.css';

/**
 * Subtle technical "blueprint" grid backdrop: faint cool-blue grid lines with
 * nodes that breathe very slowly. Throttled to ~12 fps, paused off-screen,
 * and reduced to one static frame under prefers-reduced-motion.
 */

interface ReactiveFieldProps {
  className?: string;
  spacing?: number;
}

export default function ReactiveField({
  className = '',
  spacing = 44,
}: ReactiveFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const g = canvas.getContext('2d');
    if (!g) return;

    let w = 0;
    let h = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (time: number) => {
      g.clearRect(0, 0, w, h);

      g.lineWidth = 1;
      g.strokeStyle = 'rgba(140,162,200,0.14)';
      g.beginPath();
      for (let x = spacing / 2; x < w; x += spacing) {
        g.moveTo(Math.round(x) + 0.5, 0);
        g.lineTo(Math.round(x) + 0.5, h);
      }
      for (let y = spacing / 2; y < h; y += spacing) {
        g.moveTo(0, Math.round(y) + 0.5);
        g.lineTo(w, Math.round(y) + 0.5);
      }
      g.stroke();

      const t = time * 0.00018;
      for (let gy = spacing / 2; gy < h; gy += spacing) {
        for (let gx = spacing / 2; gx < w; gx += spacing) {
          const pulse = 0.5 + 0.5 * Math.sin((gx + gy) * 0.006 + t);
          const alpha = 0.16 + 0.16 * pulse;
          g.fillStyle = `rgba(96,168,232,${alpha.toFixed(3)})`;
          g.beginPath();
          g.arc(gx, gy, 1.5, 0, Math.PI * 2);
          g.fill();
        }
      }
    };

    // Paint one frame immediately and on every resize. This does NOT rely on
    // requestAnimationFrame (which is throttled/paused in background tabs), so
    // the grid is always visible; the rAF loop below only adds the slow breathe.
    const redraw = () => {
      resize();
      draw(performance.now());
    };

    redraw();
    window.addEventListener('resize', redraw);
    const ro = new ResizeObserver(redraw);
    ro.observe(canvas);

    let raf = 0;
    let last = 0;
    const loop = (ts: number) => {
      if (ts - last > 80) {
        // ~12 fps — enough for a slow breathe, cheap on the CPU
        draw(ts);
        last = ts;
      }
      raf = requestAnimationFrame(loop);
    };
    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(raf);
      } else {
        raf = requestAnimationFrame(loop);
      }
    };

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduced) {
      document.addEventListener('visibilitychange', onVisibility);
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', redraw);
      document.removeEventListener('visibilitychange', onVisibility);
      ro.disconnect();
    };
  }, [spacing]);

  return (
    <canvas
      ref={canvasRef}
      className={`reactive-field ${className}`}
      aria-hidden="true"
    />
  );
}

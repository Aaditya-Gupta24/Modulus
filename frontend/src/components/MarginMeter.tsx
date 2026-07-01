import { useEffect, useRef, useState } from 'react';
import './MarginMeter.css';

export type MarginStatus = 'pass' | 'warn' | 'fail' | 'neutral' | 'not_modeled';

interface MarginMeterProps {
  margin: number;
  status: MarginStatus;
  animated?: boolean;
  animationDelay?: number; // ms delay before animation starts
}

export default function MarginMeter({
  margin,
  status,
  animated = true,
  animationDelay = 0,
}: MarginMeterProps) {
  const [active, setActive] = useState(!animated);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!animated) {
      setActive(true);
      return;
    }
    // Reset so re-renders re-trigger animation
    setActive(false);
    timerRef.current = setTimeout(() => setActive(true), animationDelay + 16);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [animated, animationDelay, margin]);

  if (status === 'not_modeled') {
    return (
      <div
        className="margin-meter margin-meter--not-modeled"
        role="meter"
        aria-label="Not modeled"
        aria-valuenow={0}
        aria-valuemin={-1}
        aria-valuemax={1}
      />
    );
  }

  const isNegative = margin < 0;
  const clampedAbs = Math.min(Math.abs(margin), 1);

  if (isNegative) {
    // Negative margin: fill grows LEFT from center, red
    return (
      <div
        className="margin-meter margin-meter--bipolar"
        role="meter"
        aria-label={`Margin: ${(margin * 100).toFixed(0)}%`}
        aria-valuenow={margin}
        aria-valuemin={-1}
        aria-valuemax={1}
      >
        <span className="margin-meter__center-line" aria-hidden="true" />
        <span
          className={`margin-meter__fill margin-meter__fill--negative ${active ? 'margin-meter__fill--animate' : ''}`}
          style={{ '--fill-target': `${clampedAbs * 50}%` } as React.CSSProperties}
          aria-hidden="true"
        />
      </div>
    );
  }

  // Positive margin: fill grows from left
  return (
    <div
      className={`margin-meter margin-meter--${status}`}
      role="meter"
      aria-label={`Margin: ${(margin * 100).toFixed(0)}%`}
      aria-valuenow={margin}
      aria-valuemin={0}
      aria-valuemax={1}
    >
      <span
        className={`margin-meter__fill ${active ? 'margin-meter__fill--animate' : ''}`}
        style={{ '--fill-target': `${clampedAbs * 100}%` } as React.CSSProperties}
        aria-hidden="true"
      />
    </div>
  );
}

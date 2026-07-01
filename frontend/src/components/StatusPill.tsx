import './StatusPill.css';

export type StatusValue = 'pass' | 'warn' | 'fail' | 'neutral' | 'not_modeled';

interface StatusPillProps {
  status: StatusValue;
  label: string;
}

export default function StatusPill({ status, label }: StatusPillProps) {
  return (
    <span className={`status-pill status-pill--${status}`} aria-label={`${label}: ${status}`}>
      <span className="status-pill__dot" aria-hidden="true" />
      <span className="status-pill__label">{label}</span>
    </span>
  );
}

import './Panel.css';

export type PanelStatus = 'pass' | 'warn' | 'fail' | 'neutral';

interface PanelProps {
  title?: string;
  status?: PanelStatus;
  children: React.ReactNode;
  className?: string;
}

export default function Panel({ title, status, children, className = '' }: PanelProps) {
  const hasTitle = Boolean(title);
  return (
    <div
      className={[
        'panel',
        status ? `panel--${status}` : '',
        hasTitle ? '' : 'panel--no-header',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {status && <span className="panel__status-strip" aria-hidden="true" />}
      {title && (
        <div className="panel__header">
          <span className="panel__title overline">{title}</span>
        </div>
      )}
      <div className="panel__body">{children}</div>
    </div>
  );
}

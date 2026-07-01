import './SegmentedToggle.css';

export interface Option {
  id: string;
  label: string;
  icon?: string;
}

interface SegmentedToggleProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

export default function SegmentedToggle({
  options,
  value,
  onChange,
  label,
}: SegmentedToggleProps) {
  function handleKey(id: string, e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onChange(id);
    }
    // Arrow navigation
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      const idx = options.findIndex(o => o.id === value);
      const next = options[(idx + 1) % options.length];
      onChange(next.id);
    }
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      const idx = options.findIndex(o => o.id === value);
      const prev = options[(idx - 1 + options.length) % options.length];
      onChange(prev.id);
    }
  }

  return (
    <div className="seg-toggle">
      {label && (
        <span className="seg-toggle__label overline">{label}</span>
      )}
      <div
        className="seg-toggle__track"
        role="radiogroup"
        aria-label={label ?? 'Toggle options'}
      >
        {options.map(opt => {
          const isActive = opt.id === value;
          return (
            <button
              key={opt.id}
              type="button"
              role="radio"
              aria-checked={isActive}
              className={[
                'seg-toggle__option',
                isActive ? 'seg-toggle__option--active' : '',
              ].filter(Boolean).join(' ')}
              onClick={() => onChange(opt.id)}
              onKeyDown={e => handleKey(opt.id, e)}
              tabIndex={isActive ? 0 : -1}
            >
              {opt.icon && (
                <span className="seg-toggle__icon" aria-hidden="true">
                  {opt.icon}
                </span>
              )}
              <span className="seg-toggle__text">{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

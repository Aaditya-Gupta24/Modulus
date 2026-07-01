import './ChipSelector.css';

export interface Chip {
  id: string;
  label: string;
  color?: string;
  icon?: string;
}

interface ChipSelectorProps {
  chips: Chip[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label?: string;
}

export default function ChipSelector({
  chips,
  selected,
  onChange,
  label,
}: ChipSelectorProps) {
  function toggle(id: string) {
    if (selected.includes(id)) {
      onChange(selected.filter(s => s !== id));
    } else {
      onChange([...selected, id]);
    }
  }

  function handleKey(id: string, e: React.KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle(id);
    }
  }

  return (
    <div className="chip-selector">
      {label && (
        <span className="chip-selector__label overline" aria-label={label}>
          {label}
        </span>
      )}
      <div
        className="chip-selector__chips"
        role="group"
        aria-label={label ?? 'Chip selector'}
      >
        {chips.map(chip => {
          const isSelected = selected.includes(chip.id);
          // Resolve color: use provided token or fallback to --accent
          const resolvedColor = chip.color ?? 'var(--accent)';

          return (
            <button
              key={chip.id}
              type="button"
              className={['chip', isSelected ? 'chip--selected' : ''].filter(Boolean).join(' ')}
              onClick={() => toggle(chip.id)}
              onKeyDown={e => handleKey(chip.id, e)}
              aria-pressed={isSelected}
              aria-label={chip.label}
              style={
                isSelected
                  ? ({
                      '--chip-color': resolvedColor,
                      backgroundColor: `color-mix(in srgb, ${resolvedColor} 18%, transparent)`,
                      borderColor: resolvedColor,
                      color: 'var(--text-hi)',
                    } as React.CSSProperties)
                  : undefined
              }
            >
              {/* Color dot (always visible if chip has a color) */}
              {chip.color && (
                <span
                  className="chip__color-dot"
                  style={{ background: chip.color }}
                  aria-hidden="true"
                />
              )}

              {/* Icon glyph */}
              {chip.icon && (
                <span className="chip__icon" aria-hidden="true">
                  {chip.icon}
                </span>
              )}

              {/* Label */}
              <span className="chip__label">{chip.label}</span>

              {/* Checkmark when selected */}
              {isSelected && (
                <span className="chip__check" aria-hidden="true">
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

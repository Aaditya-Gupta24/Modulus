import { useId } from 'react';
import './InputGroup.css';

interface InputGroupProps {
  label: string;
  unit?: string;
  value: number | string;
  onChange: (value: string) => void;
  type?: 'number' | 'text';
  min?: number;
  max?: number;
  step?: number;
  helperText?: string;
}

export default function InputGroup({
  label,
  unit,
  value,
  onChange,
  type = 'text',
  min,
  max,
  step,
  helperText,
}: InputGroupProps) {
  const inputId = useId();
  const helperId = useId();
  const hasHelper = Boolean(helperText);

  return (
    <div className="input-group">
      <label className="input-group__label label" htmlFor={inputId}>
        {label}
      </label>

      <div className="input-group__control">
        <input
          id={inputId}
          className={[
            'input-group__input',
            type === 'number' ? 'input-group__input--mono' : '',
            unit ? 'input-group__input--has-unit' : '',
          ].filter(Boolean).join(' ')}
          type={type}
          value={value}
          min={min}
          max={max}
          step={step}
          aria-describedby={hasHelper ? helperId : undefined}
          onChange={e => onChange(e.target.value)}
          /* Remove browser default spinners; we keep the native type
             for semantics/mobile keyboards but hide the UI widget */
          onWheel={e => (e.target as HTMLInputElement).blur()}
        />
        {unit && (
          <span className="input-group__unit" aria-hidden="true">
            {unit}
          </span>
        )}
      </div>

      {hasHelper && (
        <p id={helperId} className="input-group__helper">
          {helperText}
        </p>
      )}
    </div>
  );
}

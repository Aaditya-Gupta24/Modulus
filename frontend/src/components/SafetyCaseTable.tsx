import './SafetyCaseTable.css';
import StatusPill from './StatusPill';
import type { StatusValue } from './StatusPill';
import MarginMeter from './MarginMeter';

export interface CheckRow {
  name: string;
  actual: number;
  allowable: number;
  margin: number;
  status: 'pass' | 'fail' | 'warning' | 'not_modeled';
  notes: string;
}

interface SafetyCaseTableProps {
  checks: CheckRow[];
  animate?: boolean;
}

// Map machine names to human-friendly labels
const LABEL_MAP: Record<string, string> = {
  bending_stress:   'Bending Stress',
  deflection:       'Deflection',
  euler_buckling:   'Euler Buckling',
  shear_stress:     'Shear Stress',
  torsion:          'Torsion',
  local_buckling:   'Local Buckling',
  bearing_stress:   'Bearing Stress',
  fatigue:          'Fatigue',
  von_mises:        'Von Mises',
  bolt_shear:       'Bolt Shear',
  bolt_tension:     'Bolt Tension',
  plate_bending:    'Plate Bending',
  weld_throat:      'Weld Throat',
  contact_pressure: 'Contact Pressure',
};

function humanLabel(name: string): string {
  if (LABEL_MAP[name]) return LABEL_MAP[name];
  // Fallback: title-case the snake_case key
  return name
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

// Convert status string to the StatusPill StatusValue type
function toStatusValue(status: CheckRow['status']): StatusValue {
  if (status === 'warning') return 'warn';
  if (status === 'not_modeled') return 'not_modeled';
  return status; // 'pass' | 'fail'
}

function toMarginStatus(status: CheckRow['status']): 'pass' | 'warn' | 'fail' | 'neutral' | 'not_modeled' {
  if (status === 'warning') return 'warn';
  return status as 'pass' | 'fail' | 'not_modeled';
}

function pillLabel(status: CheckRow['status']): string {
  switch (status) {
    case 'pass':        return 'Pass';
    case 'fail':        return 'Fail';
    case 'warning':     return 'Warning';
    case 'not_modeled': return 'Not Modeled';
    default:            return status;
  }
}

// Heuristic formatting: values >= 1e3 treated as Pa → shown as MPa
// Values <= 0.1 treated as m → shown as mm
function formatValue(v: number): { value: string; unit: string } {
  if (Math.abs(v) >= 1e3) {
    return { value: (v / 1e6).toFixed(2), unit: 'MPa' };
  }
  if (Math.abs(v) < 0.1 && v !== 0) {
    return { value: (v * 1000).toFixed(3), unit: 'mm' };
  }
  return { value: v.toFixed(3), unit: '' };
}

export default function SafetyCaseTable({ checks, animate = true }: SafetyCaseTableProps) {
  if (checks.length === 0) {
    return (
      <div className="sct__empty" role="status">
        No checks to display.
      </div>
    );
  }

  return (
    <div className="sct-wrap">
      <table className="sct" aria-label="Safety case checks">
        <thead className="sct__head">
          <tr>
            <th className="sct__th sct__th--check" scope="col">Check</th>
            <th className="sct__th sct__th--num" scope="col">Value</th>
            <th className="sct__th sct__th--num" scope="col">Limit</th>
            <th className="sct__th sct__th--margin" scope="col">Margin</th>
            <th className="sct__th sct__th--status" scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {checks.map((row, i) => {
            const isNotModeled = row.status === 'not_modeled';
            const actualFmt = formatValue(row.actual);
            const allowFmt  = formatValue(row.allowable);
            const pct       = `${(row.margin * 100).toFixed(0)}%`;
            const delay     = animate ? i * 40 : 0;

            return (
              <tr
                key={row.name}
                className={[
                  'sct__row',
                  isNotModeled ? 'sct__row--not-modeled' : '',
                  i % 2 === 1 ? 'sct__row--zebra' : '',
                ].filter(Boolean).join(' ')}
              >
                {/* Check name */}
                <td className="sct__td sct__td--check">
                  <span className="sct__check-label">{humanLabel(row.name)}</span>
                  {row.notes && (
                    <span className="sct__check-notes">{row.notes}</span>
                  )}
                </td>

                {/* Actual value */}
                <td className="sct__td sct__td--num" aria-label={`Actual: ${actualFmt.value} ${actualFmt.unit}`}>
                  <span className="sct__num">
                    {isNotModeled ? <span className="sct__na">N/A</span> : (
                      <>
                        {actualFmt.value}
                        {actualFmt.unit && <span className="sct__unit">{actualFmt.unit}</span>}
                      </>
                    )}
                  </span>
                </td>

                {/* Allowable value */}
                <td className="sct__td sct__td--num" aria-label={`Limit: ${allowFmt.value} ${allowFmt.unit}`}>
                  <span className="sct__num">
                    {isNotModeled ? <span className="sct__na">N/A</span> : (
                      <>
                        {allowFmt.value}
                        {allowFmt.unit && <span className="sct__unit">{allowFmt.unit}</span>}
                      </>
                    )}
                  </span>
                </td>

                {/* Margin bar + percentage */}
                <td className="sct__td sct__td--margin">
                  <div className="sct__margin-cell">
                    <MarginMeter
                      margin={isNotModeled ? 0 : row.margin}
                      status={toMarginStatus(row.status)}
                      animated={animate}
                      animationDelay={delay}
                    />
                    <span className="sct__margin-pct">
                      {isNotModeled ? <span className="sct__na">—</span> : pct}
                    </span>
                  </div>
                </td>

                {/* Status pill */}
                <td className="sct__td sct__td--status">
                  <StatusPill
                    status={toStatusValue(row.status)}
                    label={pillLabel(row.status)}
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

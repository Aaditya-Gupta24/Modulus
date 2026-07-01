import { useState, useMemo, useCallback } from 'react';
import './DataTable.css';

export interface Column {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
  mono?: boolean;
  format?: (value: unknown) => string;
  sortable?: boolean;
}

interface DataTableProps {
  columns: Column[];
  rows: Record<string, unknown>[];
  maxRows?: number;
  onRowClick?: (row: Record<string, unknown>) => void;
  highlightIndex?: number;
}

type SortDir = 'asc' | 'desc';

interface SortState {
  key: string;
  dir: SortDir;
}

function defaultFormat(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') {
    if (!isFinite(value)) return '—';
    // Large numbers: format as MPa; small: as mm; otherwise 3dp
    if (Math.abs(value) >= 1e3) return `${(value / 1e6).toFixed(2)} MPa`;
    if (Math.abs(value) < 0.1 && value !== 0) return `${(value * 1000).toFixed(3)} mm`;
    return value.toFixed(3);
  }
  return String(value);
}

export default function DataTable({
  columns,
  rows,
  maxRows,
  onRowClick,
  highlightIndex,
}: DataTableProps) {
  const [sort, setSort] = useState<SortState | null>(null);

  const handleHeaderClick = useCallback(
    (col: Column) => {
      if (!col.sortable) return;
      setSort(prev => {
        if (prev?.key === col.key) {
          return { key: col.key, dir: prev.dir === 'asc' ? 'desc' : 'asc' };
        }
        return { key: col.key, dir: 'asc' };
      });
    },
    [],
  );

  const handleHeaderKey = useCallback(
    (col: Column, e: React.KeyboardEvent) => {
      if (!col.sortable) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleHeaderClick(col);
      }
    },
    [handleHeaderClick],
  );

  const sortedRows = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sort]);

  const visibleRows = maxRows != null ? sortedRows.slice(0, maxRows) : sortedRows;

  if (columns.length === 0) {
    return <div className="dtable__empty">No columns defined.</div>;
  }

  return (
    <div className="dtable-outer">
      <div className="dtable-scroll">
        <table className="dtable" aria-label="Data table" aria-rowcount={visibleRows.length}>
          <thead className="dtable__head">
            <tr>
              {columns.map((col, ci) => {
                const isSorted = sort?.key === col.key;
                const dir = isSorted ? sort!.dir : null;
                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={[
                      'dtable__th',
                      col.sortable ? 'dtable__th--sortable' : '',
                      isSorted ? 'dtable__th--sorted' : '',
                      ci === 0 ? 'dtable__th--frozen' : '',
                    ].filter(Boolean).join(' ')}
                    style={{ textAlign: col.align ?? (col.mono ? 'right' : 'left') }}
                    aria-sort={isSorted ? (dir === 'asc' ? 'ascending' : 'descending') : undefined}
                    tabIndex={col.sortable ? 0 : undefined}
                    onClick={() => handleHeaderClick(col)}
                    onKeyDown={e => handleHeaderKey(col, e)}
                  >
                    <span className="dtable__th-inner">
                      <span>{col.label}</span>
                      {col.sortable && (
                        <span className="dtable__sort-indicator" aria-hidden="true">
                          {isSorted
                            ? dir === 'asc' ? '▲' : '▼'
                            : '⇅'}
                        </span>
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="dtable__td dtable__td--empty">
                  No data.
                </td>
              </tr>
            ) : (
              visibleRows.map((row, ri) => {
                const isHighlighted = ri === highlightIndex;
                const isClickable = Boolean(onRowClick);
                return (
                  <tr
                    key={ri}
                    className={[
                      'dtable__row',
                      ri % 2 === 1 ? 'dtable__row--zebra' : '',
                      isHighlighted ? 'dtable__row--highlight' : '',
                      isClickable ? 'dtable__row--clickable' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => onRowClick?.(row)}
                    onKeyDown={e => {
                      if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        onRowClick?.(row);
                      }
                    }}
                    tabIndex={isClickable ? 0 : undefined}
                    aria-selected={isHighlighted || undefined}
                  >
                    {columns.map((col, ci) => {
                      const raw = row[col.key];
                      const display = col.format ? col.format(raw) : defaultFormat(raw);
                      const isMono = col.mono ?? false;
                      const align = col.align ?? (isMono ? 'right' : 'left');
                      return (
                        <td
                          key={col.key}
                          className={[
                            'dtable__td',
                            isMono ? 'dtable__td--mono' : '',
                            ci === 0 ? 'dtable__td--frozen' : '',
                          ].filter(Boolean).join(' ')}
                          style={{ textAlign: align }}
                        >
                          {display}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {maxRows != null && rows.length > maxRows && (
        <div className="dtable__overflow-note" role="status">
          Showing {maxRows} of {rows.length} rows
        </div>
      )}
    </div>
  );
}

import { useState, useRef, useCallback } from 'react';
import './Sidebar.css';

export type ViewId =
  | 'dashboard'
  | 'beam-optimizer'
  | 'bracket-analysis'
  | 'compare'
  | 'validation'
  | 'assumptions'
  | 'settings';

interface NavItem {
  id: ViewId;
  icon: string;
  label: string;
  description: string;
}

const TOP_NAV: NavItem[] = [
  { id: 'dashboard',        icon: '▣', label: 'Dashboard',        description: 'Overview and quick metrics' },
  { id: 'beam-optimizer',   icon: '◧', label: 'Beam Optimizer',   description: 'Sweep materials & sections' },
  { id: 'bracket-analysis', icon: '⟁', label: 'Bracket Analysis', description: 'Plate, bolts & gusset checks' },
  { id: 'compare',          icon: '⊞', label: 'Compare',          description: 'Side-by-side candidate review' },
  { id: 'validation',       icon: '⚗', label: 'Validation',       description: 'FEA vs analytical results' },
  { id: 'assumptions',      icon: 'ⓘ', label: 'Assumptions',      description: 'Model limits & constraints' },
];

const BOTTOM_NAV: NavItem[] = [
  { id: 'settings', icon: '⚙', label: 'Settings', description: 'Units, preferences, display' },
];

interface TooltipState {
  visible: boolean;
  label: string;
  description: string;
  y: number;
}

interface SidebarProps {
  activeView: ViewId;
  onNavigate: (id: ViewId) => void;
}

export default function Sidebar({ activeView, onNavigate }: SidebarProps) {
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    label: '',
    description: '',
    y: 0,
  });
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isExpanded = pinned || hovered;

  const handleMouseEnterSidebar = useCallback(() => {
    setHovered(true);
  }, []);

  const handleMouseLeaveSidebar = useCallback(() => {
    setHovered(false);
    // Hide tooltip when leaving sidebar entirely
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    setTooltip(prev => ({ ...prev, visible: false }));
  }, []);

  const handleItemMouseEnter = useCallback(
    (item: NavItem, e: React.MouseEvent<HTMLButtonElement>) => {
      if (isExpanded) return; // No tooltip when expanded — label is visible
      const rect = e.currentTarget.getBoundingClientRect();
      if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = setTimeout(() => {
        setTooltip({
          visible: true,
          label: item.label,
          description: item.description,
          y: rect.top + rect.height / 2,
        });
      }, 300);
    },
    [isExpanded],
  );

  const handleItemMouseLeave = useCallback(() => {
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    setTooltip(prev => ({ ...prev, visible: false }));
  }, []);

  const renderNavItem = (item: NavItem) => {
    const isActive = activeView === item.id;
    return (
      <button
        key={item.id}
        className={`sidebar__item ${isActive ? 'sidebar__item--active' : ''}`}
        onClick={() => onNavigate(item.id)}
        onMouseEnter={e => handleItemMouseEnter(item, e)}
        onMouseLeave={handleItemMouseLeave}
        aria-label={item.label}
        aria-current={isActive ? 'page' : undefined}
        title=""
      >
        {isActive && <span className="sidebar__item-bar" aria-hidden="true" />}
        <span
          className="sidebar__item-icon"
          aria-hidden="true"
          style={item.id === 'validation' ? { transform: 'scaleY(-1)' } : undefined}
        >{item.icon}</span>
        <span className="sidebar__item-label">{item.label}</span>
      </button>
    );
  };

  return (
    <>
      <nav
        className={`sidebar ${isExpanded ? 'sidebar--expanded' : ''}`}
        onMouseEnter={handleMouseEnterSidebar}
        onMouseLeave={handleMouseLeaveSidebar}
        aria-label="Main navigation"
      >
        {/* Logo mark */}
        <div className="sidebar__logo" aria-hidden="true">
          <svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" className="sidebar__hex">
            <polygon
              points="14,1.5 25,8 25,20 14,26.5 3,20 3,8"
              fill="var(--bg-panel)"
              stroke="var(--accent)"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <polygon
              points="14,6.5 20,10 20,18 14,21.5 8,18 8,10"
              fill="var(--accent)"
              opacity="0.2"
            />
            <text x="14" y="17.5" textAnchor="middle" fontFamily="Inter, sans-serif" fontSize="9" fontWeight="700" fill="var(--accent)">M</text>
          </svg>
          <span className="sidebar__brand-name">Modulus</span>
        </div>

        {/* Top nav */}
        <div className="sidebar__section sidebar__section--top">
          {TOP_NAV.map(renderNavItem)}
        </div>

        {/* Divider */}
        <div className="sidebar__divider" role="separator" />

        {/* Bottom nav */}
        <div className="sidebar__section sidebar__section--bottom">
          {BOTTOM_NAV.map(renderNavItem)}

          {/* Pin toggle */}
          <button
            className={`sidebar__pin ${pinned ? 'sidebar__pin--active' : ''}`}
            onClick={() => setPinned(p => !p)}
            aria-label={pinned ? 'Unpin sidebar' : 'Pin sidebar open'}
            aria-pressed={pinned}
          >
            <span className="sidebar__item-icon" aria-hidden="true">
              {pinned ? '◀' : '▶'}
            </span>
            <span className="sidebar__item-label">{pinned ? 'Unpin' : 'Pin open'}</span>
          </button>
        </div>
      </nav>

      {/* Tooltip portal — rendered outside sidebar so it overlaps main content */}
      {tooltip.visible && !isExpanded && (
        <div
          className="sidebar-tooltip"
          style={{ top: tooltip.y }}
          role="tooltip"
          aria-hidden="true"
        >
          <span className="sidebar-tooltip__arrow" />
          <span className="sidebar-tooltip__label">{tooltip.label}</span>
          <span className="sidebar-tooltip__desc">{tooltip.description}</span>
        </div>
      )}
    </>
  );
}

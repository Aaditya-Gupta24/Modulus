import { useState, useCallback } from 'react';
import Sidebar, { type ViewId } from './components/Sidebar';
import TopBar from './components/TopBar';
import Dashboard from './views/Dashboard';
import BeamOptimizer from './views/BeamOptimizer';
import BracketAnalysis from './views/BracketAnalysis';
import Compare from './views/Compare';
import Validation from './views/Validation';
import Assumptions from './views/Assumptions';
import Settings from './views/Settings';
import './App.css';

const VIEW_TITLES: Record<ViewId, string> = {
  'dashboard':        'Dashboard',
  'beam-optimizer':   'Beam Optimizer',
  'bracket-analysis': 'Bracket Analysis',
  'compare':          'Compare',
  'validation':       'Validation',
  'assumptions':      'Assumptions',
  'settings':         'Settings',
};

/* Views where unit chip + export controls are relevant */
const ANALYSIS_VIEWS = new Set<ViewId>([
  'beam-optimizer',
  'bracket-analysis',
  'compare',
]);

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>('dashboard');

  const handleNavigate = useCallback((id: ViewId) => {
    setActiveView(id);
  }, []);

  const showControls = ANALYSIS_VIEWS.has(activeView);

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':        return <Dashboard onNavigate={handleNavigate} />;
      case 'beam-optimizer':   return <BeamOptimizer />;
      case 'bracket-analysis': return <BracketAnalysis />;
      case 'compare':          return <Compare />;
      case 'validation':       return <Validation />;
      case 'assumptions':      return <Assumptions />;
      case 'settings':         return <Settings />;
      default:                 return <Dashboard onNavigate={handleNavigate} />;
    }
  };

  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} onNavigate={handleNavigate} />

      <div className="app-main">
        <TopBar
          viewTitle={VIEW_TITLES[activeView]}
          showUnitChip={showControls}
          showExport={showControls}
        />

        <main className="app-content" id="main-content">
          {/* Key forces React to remount + animate on view change */}
          <div className="app-view-transition" key={activeView}>
            {renderView()}
          </div>
        </main>
      </div>
    </div>
  );
}

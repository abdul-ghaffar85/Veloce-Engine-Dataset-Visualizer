import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDashboardStore } from '../store/useDashboardStore';
import { ArrowLeft, Plus, Undo2, Redo2, CheckCircle2, Edit3, Eye } from 'lucide-react';

import { DashboardCanvas } from '../components/dashboard/DashboardCanvas';
import { DashboardPropertiesPanel } from '../components/dashboard/DashboardPropertiesPanel';

export const DashboardBuilderView: React.FC = () => {
  const { datasetId, dashboardId } = useParams<{ datasetId: string; dashboardId: string }>();
  const navigate = useNavigate();
  const { dashboards, updateDashboard, undo, redo, history, setActiveDashboardId, setActiveWidgetId, loadState } = useDashboardStore();
  const [saveIndicator, setSaveIndicator] = useState(false);
  const [showAddWidget, setShowAddWidget] = React.useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editName, setEditName] = useState('');
  const [hasLoaded, setHasLoaded] = useState(false);
  const { savedCharts, addWidget } = useDashboardStore();
  const datasetCharts = Object.values(savedCharts).filter(c => c.datasetId === datasetId);

  const dashboard = dashboardId ? dashboards[dashboardId] : null;

  useEffect(() => {
    loadState();
    setHasLoaded(true);
    if (dashboardId) {
      setActiveDashboardId(dashboardId);
    }
    return () => {
      setActiveDashboardId(null);
      setActiveWidgetId(null);
    };
  }, [dashboardId, setActiveDashboardId, setActiveWidgetId, loadState]);

  useEffect(() => {
    // Wait for loadState() to hydrate the store before deciding the
    // dashboard is genuinely missing — otherwise a direct link/refresh
    // bounces straight back to the list before persisted state loads.
    if (hasLoaded && !dashboard && datasetId) {
      navigate(`/dataset/${datasetId}/dashboards`);
    }
  }, [hasLoaded, dashboard, datasetId, navigate]);

  // Sync editName when dashboard changes
  useEffect(() => {
    if (dashboard && !isEditingTitle) {
      setEditName(dashboard.name);
    }
  }, [dashboard, isEditingTitle]);

  useEffect(() => {
    if (dashboard) {
      setSaveIndicator(true);
      const timer = setTimeout(() => setSaveIndicator(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [dashboard?.updatedAt]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = document.activeElement?.tagName.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        const state = useDashboardStore.getState();
        if (state.activeWidgetId && !dashboard?.isLocked) {
          useDashboardStore.getState().duplicateWidget(state.activeWidgetId);
        }
      }

      if (e.key === 'Delete' || e.key === 'Backspace') {
        const state = useDashboardStore.getState();
        if (state.activeWidgetId && !dashboard?.isLocked) {
          useDashboardStore.getState().removeWidget(state.activeWidgetId);
          useDashboardStore.getState().setActiveWidgetId(null);
        }
      }

      if (e.key === 'F2') {
        e.preventDefault();
        const state = useDashboardStore.getState();
        if (state.activeWidgetId && !dashboard?.isLocked) {
          window.dispatchEvent(new CustomEvent('veloce-rename-widget', { detail: { id: state.activeWidgetId } }));
        } else if (!state.activeWidgetId && !dashboard?.isLocked) {
          setIsEditingTitle(true);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, dashboard?.isLocked]);

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Dashboard not found.
      </div>
    );
  }

  const handleNameSave = () => {
    if (editName.trim() !== '') {
      updateDashboard(dashboard.id, { name: editName });
    } else {
      setEditName(dashboard.name);
    }
    setIsEditingTitle(false);
  };

  const toggleLock = () => {
    updateDashboard(dashboard.id, { isLocked: !dashboard.isLocked });
    if (!dashboard.isLocked) {
      setActiveWidgetId(null); // deselect widget when entering view mode
    }
  };

  return (
    <div className="h-full flex flex-col bg-dark-900 fade-in" onClick={() => setActiveWidgetId(null)}>
      {/* Dashboard Topbar */}
      <div className="h-14 border-b border-dark-700 bg-dark-800 flex items-center justify-between px-4 shrink-0 relative z-20" onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/dataset/${datasetId}/dashboards`)}
            className="p-2 hover:bg-dark-700 text-gray-400 hover:text-white rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex flex-col">
            {isEditingTitle ? (
              <input
                autoFocus
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={handleNameSave}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleNameSave();
                  if (e.key === 'Escape') {
                    setEditName(dashboard.name);
                    setIsEditingTitle(false);
                  }
                }}
                className="bg-dark-700 border border-brand-500 text-lg font-semibold text-white focus:outline-none focus:ring-2 focus:ring-brand-500 rounded px-2 py-0.5 w-64"
              />
            ) : (
              <h1 
                onDoubleClick={() => setIsEditingTitle(true)}
                className="text-lg font-semibold text-white px-2 py-0.5 cursor-text hover:bg-dark-700 rounded transition-colors w-64 truncate"
                title="Double click to rename"
              >
                {dashboard.name}
              </h1>
            )}
            <div className={`text-[10px] px-2 flex items-center gap-1 transition-opacity ${saveIndicator ? 'opacity-100 text-brand-400' : 'opacity-0'}`}>
              <CheckCircle2 className="w-3 h-3" /> Auto-saved
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2 relative">
          {!dashboard.isLocked && (
            <>
              <button 
                onClick={undo}
                disabled={history.past.length === 0}
                className={`p-2 rounded-lg transition-colors ${history.past.length === 0 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-dark-700'}`}
                title="Undo (Ctrl+Z)"
              >
                <Undo2 className="w-4 h-4" />
              </button>
              <button 
                onClick={redo}
                disabled={history.future.length === 0}
                className={`p-2 rounded-lg transition-colors mr-2 ${history.future.length === 0 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-dark-700'}`}
                title="Redo (Ctrl+Shift+Z)"
              >
                <Redo2 className="w-4 h-4" />
              </button>
            </>
          )}

          <button 
            onClick={toggleLock}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium ${
              dashboard.isLocked 
                ? 'bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 border border-brand-500/30' 
                : 'text-gray-300 hover:text-white bg-dark-700 hover:bg-dark-600 border border-dark-600'
            }`}
          >
            {dashboard.isLocked ? (
              <><Eye className="w-4 h-4" /> View Mode</>
            ) : (
              <><Edit3 className="w-4 h-4" /> Edit Mode</>
            )}
          </button>

          {!dashboard.isLocked && (
            <button 
              onClick={() => setShowAddWidget(!showAddWidget)}
              className="px-3 py-1.5 ml-2 flex items-center gap-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-dark-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Widget
            </button>
          )}
          
          {showAddWidget && !dashboard.isLocked && (
            <div className="absolute top-full right-0 mt-2 w-64 bg-dark-800 border border-dark-700 rounded-xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2">
              <div className="p-2 border-b border-dark-700 font-medium text-sm text-gray-400">Add Saved Chart</div>
              <div className="max-h-64 overflow-y-auto custom-scrollbar">
                {datasetCharts.length === 0 ? (
                  <div className="p-4 text-center text-sm text-gray-500">No saved charts. Create them in the Chart Builder.</div>
                ) : (
                  datasetCharts.map(chart => (
                    <button
                      key={chart.id}
                      onClick={() => {
                        addWidget({ type: 'chart', chartId: chart.id, title: chart.title });
                        setShowAddWidget(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-dark-700 hover:text-white transition-colors"
                    >
                      {chart.title}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Dashboard Canvas Area */}
        <div className="flex-1 overflow-auto bg-dark-950 relative custom-scrollbar">
          <DashboardCanvas isLocked={!!dashboard.isLocked} />
        </div>
        
        {/* Properties Panel (Visible in Edit Mode) */}
        {!dashboard.isLocked && (
          <div onClick={e => e.stopPropagation()}>
            <DashboardPropertiesPanel />
          </div>
        )}
      </div>
    </div>
  );
};

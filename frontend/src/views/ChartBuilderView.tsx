import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2, LayoutGrid, FileText, Plus, Sparkles, Save, Download, Undo, Redo } from 'lucide-react';
import { PreviewTable } from '../components/PreviewTable';
import { InsightsPanel } from '../components/InsightsPanel';
import { Sidebar } from '../components/Sidebar';
import { PropertiesPanel } from '../components/PropertiesPanel';
import { WidgetRenderer } from '../components/WidgetRenderer';
import { GlobalSlicers } from '../components/GlobalSlicers';
import { DndContext } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import { useDatasetStore } from '../store/useDatasetStore';
import { datasetsApi } from '../api/datasets';
import { dashboardsApi } from '../api/dashboards';
import type { Widget } from '../store/useDatasetStore';

// @ts-ignore
import { Responsive, WidthProvider } from 'react-grid-layout/legacy';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

export const ChartBuilderView: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { 
    setActiveDatasetId, setDatasetMetadata, datasetMetadata, setFieldSchema,
    widgets, selectedWidgetId, setSelectedWidgetId, addWidget, updateWidgetLayout, updateWidgetConfig, addGlobalFilter,
    dashboardName, setDashboardName, saveDashboard, loadDashboard, undo, redo, historyIndex, history
  } = useDatasetStore();
  
  const [isLoadedFromStorage, setIsLoadedFromStorage] = React.useState(false);
  
  // 'canvas' | 'data' | 'insights'
  const [activeView, setActiveView] = React.useState<'canvas' | 'data' | 'insights'>('canvas');

  useEffect(() => {
    if (datasetId) {
      setActiveDatasetId(datasetId);
      const loaded = loadDashboard(datasetId);
      setIsLoadedFromStorage(loaded);
    }
  }, [datasetId, setActiveDatasetId, loadDashboard]);

  // Fetch Dataset Metadata if not loaded
  const { data: metadataQuery } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => datasetsApi.getMetadata(datasetId!),
    enabled: !!datasetId && !datasetMetadata,
  });

  useEffect(() => {
    if (metadataQuery?.dataset) {
      setDatasetMetadata(metadataQuery.dataset);
    }
  }, [metadataQuery, setDatasetMetadata]);

  // Fetch Dashboard Layout if not loaded from storage
  const { data: dashboardRes, isLoading: isLoadingDashboard, error: dashboardError } = useQuery({
    queryKey: ['dashboard', datasetId],
    queryFn: () => dashboardsApi.generate(datasetId!),
    enabled: !!datasetId && !isLoadedFromStorage,
  });

  // Handle auto-generated dashboard layout payload if loaded
  useEffect(() => {
    if (dashboardRes?.dashboard && !isLoadedFromStorage && widgets.length === 0) {
       setDashboardName(dashboardRes.dashboard.title || 'Analytics Dashboard');
       // Real auto-generation logic would parse the dashboardRes.dashboard structure and create widgets.
       // We keep it empty if none was stored so the user can build from scratch.
    }
  }, [dashboardRes, isLoadedFromStorage, widgets.length, setDashboardName]);

  // Fetch Dataset Profile
  const { isLoading: isLoadingProfile } = useQuery({
    queryKey: ['profile', datasetId],
    queryFn: () => datasetsApi.getProfile(datasetId!),
    enabled: !!datasetId,
  });

  // Fetch Dataset Schema
  const { data: schemaRes, isLoading: isLoadingSchema } = useQuery({
    queryKey: ['schema', datasetId],
    queryFn: () => datasetsApi.getSchema(datasetId!),
    enabled: !!datasetId,
  });

  useEffect(() => {
    if (schemaRes?.schema) {
      setFieldSchema(schemaRes.schema);
    }
  }, [schemaRes, setFieldSchema]);

  if ((isLoadingDashboard && !isLoadedFromStorage) || isLoadingProfile || isLoadingSchema || !datasetId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="w-12 h-12 text-brand-500 animate-spin mb-4" />
        <h3 className="text-xl font-medium text-white">Generating AI Dashboard...</h3>
        <p className="text-gray-400 mt-2">Running profiling, correlations, and semantic engines</p>
      </div>
    );
  }

  if (dashboardError && !isLoadedFromStorage) {
    return (
      <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">
        <h3 className="font-semibold text-lg">Failed to generate dashboard</h3>
        <p className="mt-1 text-sm">{dashboardError.message}</p>
      </div>
    );
  }

  const handleExport = () => {
    const payload = {
      dashboardName,
      widgets,
      globalFilters: useDatasetStore.getState().globalFilters
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dashboardName.replace(/\s+/g, '_')}_export.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    if (activeView !== 'canvas' || !selectedWidgetId) return;

    const { active, over } = event;
    if (!over) return;
    
    const field = active.data.current?.field;
    if (!field) return;

    const currentWidget = widgets.find((w: Widget) => w.id === selectedWidgetId);
    if (!currentWidget) return;

    if (over.id === 'xAxis') {
      updateWidgetConfig(selectedWidgetId, { xAxis: field });
    } else if (over.id === 'yAxis') {
      updateWidgetConfig(selectedWidgetId, { yAxis: field });
    } else if (over.id === 'color') {
      updateWidgetConfig(selectedWidgetId, { color: field });
    } else if (over.id === 'size') {
      updateWidgetConfig(selectedWidgetId, { size: field });
    } else if (over.id === 'filters') {
      updateWidgetConfig(selectedWidgetId, { 
        filters: [
          ...(currentWidget.config.filters || []),
          {
            id: Math.random().toString(36).substr(2, 9),
            field,
            operator: 'eq',
            value: ''
          }
        ] 
      });
    } else if (over.id === 'globalSlicers') {
      addGlobalFilter({
        id: Math.random().toString(36).substr(2, 9),
        field,
        operator: 'eq',
        value: ''
      });
    }
  };

  const handleLayoutChange = (currentLayout: readonly any[]) => {
    updateWidgetLayout(currentLayout as any[]);
  };

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex gap-0 animate-in fade-in duration-500 items-start h-[calc(100vh-theme(spacing.16))]">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-transparent">
          
          {/* Top Toolbar */}
          <div className="flex items-center justify-between border-b border-dark-700/50 bg-dark-800/60 backdrop-blur-md px-6 py-3 shrink-0 relative z-10 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <LayoutGrid className="w-5 h-5 text-brand-400" />
                <input
                  type="text"
                  value={dashboardName}
                  onChange={(e) => setDashboardName(e.target.value)}
                  className="text-xl font-bold text-white bg-transparent outline-none hover:bg-dark-700 focus:bg-dark-900 px-1 py-0.5 rounded transition-colors"
                />
              </div>
              <p className="text-gray-400 text-sm flex items-center gap-2 mt-0.5 px-1">
                <FileText className="w-3.5 h-3.5" />
                {datasetMetadata?.original_filename || datasetId}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => undo()}
                disabled={historyIndex <= 0}
                className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-dark-700 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                title="Undo"
              >
                <Undo className="w-4 h-4" />
              </button>
              <button
                onClick={() => redo()}
                disabled={historyIndex >= history.length - 1}
                className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-dark-700 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                title="Redo"
              >
                <Redo className="w-4 h-4" />
              </button>

              <div className="w-px h-6 bg-dark-600 mx-1"></div>

              <button
                onClick={saveDashboard}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-dark-700 transition-colors"
              >
                <Save className="w-4 h-4" /> Save
              </button>
              <button
                onClick={handleExport}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-dark-700 transition-colors"
              >
                <Download className="w-4 h-4" /> Export
              </button>

              <div className="w-px h-6 bg-dark-600 mx-1"></div>

              <button
                onClick={() => setActiveView('canvas')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeView === 'canvas' ? 'bg-brand-500/20 text-brand-400' : 'text-gray-400 hover:bg-dark-700'
                }`}
              >
                Canvas
              </button>
              <button
                onClick={() => setActiveView('data')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeView === 'data' ? 'bg-brand-500/20 text-brand-400' : 'text-gray-400 hover:bg-dark-700'
                }`}
              >
                Data Grid
              </button>
              <button
                onClick={() => setActiveView('insights')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeView === 'insights' ? 'bg-brand-500/20 text-brand-400' : 'text-gray-400 hover:bg-dark-700'
                }`}
              >
                <Sparkles className="w-4 h-4 inline-block mr-1" /> Insights
              </button>
              
              <div className="w-px h-6 bg-dark-600 mx-2"></div>
              
              <button
                onClick={() => addWidget('chart')}
                className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-brand-600 hover:bg-brand-500 text-white transition-colors text-sm font-medium shadow-sm"
              >
                <Plus className="w-4 h-4" /> Add Widget
              </button>
            </div>
          </div>

          {/* Canvas Area */}
          <div className="flex-1 overflow-auto p-6">
            {activeView === 'data' && (
              <div className="bg-dark-800 border border-dark-700 rounded-xl p-5 shadow-lg h-full flex flex-col animate-in fade-in zoom-in-95 duration-300">
                <h3 className="text-lg font-semibold text-white mb-4">Dataset Preview</h3>
                <div className="flex-1 overflow-hidden">
                  <PreviewTable datasetId={datasetId} />
                </div>
              </div>
            )}
            
            {activeView === 'insights' && (
              <InsightsPanel datasetId={datasetId} />
            )}

            {activeView === 'canvas' && (
              <div className="animate-in fade-in duration-300 min-h-full flex flex-col">
                <GlobalSlicers />
                {widgets.length === 0 ? (
                  <div className="flex flex-col items-center justify-center flex-1 text-gray-500">
                    <LayoutGrid className="w-16 h-16 opacity-20 mb-4" />
                    <p className="text-lg">Your dashboard is empty</p>
                    <p className="text-sm mt-1 mb-6">Add a widget to start building your layout</p>
                    <button
                      onClick={() => addWidget('chart')}
                      className="px-4 py-2 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-500 transition-colors"
                    >
                      Add First Widget
                    </button>
                  </div>
                ) : (
                  <div className="flex-1">
                    <ResponsiveGridLayout
                      className="layout"
                      layouts={{ lg: widgets.map((w: Widget) => w.layout) }}
                      cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                      rowHeight={100}
                      onLayoutChange={handleLayoutChange}
                      draggableHandle=".widget-drag-handle"
                      margin={[16, 16]}
                    >
                      {widgets.map((widget: Widget) => (
                        <div 
                          key={widget.id} 
                          onClick={() => setSelectedWidgetId(widget.id)}
                          className={`relative group rounded-lg overflow-hidden transition-shadow ${
                            selectedWidgetId === widget.id ? 'ring-2 ring-brand-500 shadow-lg shadow-brand-500/20' : 'hover:ring-1 hover:ring-dark-500'
                          }`}
                        >
                          {/* Invisible Drag Handle Overlay over header area */}
                          <div className="widget-drag-handle absolute top-0 left-0 right-0 h-10 z-20 cursor-move"></div>
                          <WidgetRenderer datasetId={datasetId} widget={widget} />
                        </div>
                      ))}
                    </ResponsiveGridLayout>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Properties Panel */}
        {activeView === 'canvas' && (
          <PropertiesPanel />
        )}
      </div>
    </DndContext>
  );
};

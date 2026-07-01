import { create } from 'zustand';
import type { DatasetMetadata, DatasetFieldSchema, FieldDescriptor } from '../api/datasets';

export interface FilterState {
  id: string; // unique ID so we can have multiple filters for the same field
  field: FieldDescriptor;
  operator: string;
  value: string;
}

export type ChartType = 
  | 'bar' | 'column' | 'horizontalBar' | 'groupedBar' | 'stackedBar' 
  | 'line' | 'area' | 'spline' 
  | 'histogram' | 'boxplot' 
  | 'pie' | 'doughnut' | 'treemap' 
  | 'scatter' | 'bubble' 
  | 'heatmap' | 'radar' | 'waterfall' | 'funnel' | 'gauge' 
  | 'table' | 'pivotTable' 
  | 'kpi' | 'metric';

export interface ChartConfig {
  xAxis: FieldDescriptor | null;
  yAxis: FieldDescriptor | null;
  color: FieldDescriptor | null;
  size: FieldDescriptor | null; // For Bubble charts
  yAggregation: string;
  filters: FilterState[];
  sortBy: string | null;
  sortOrder: 'asc' | 'desc';
  limit: number | null;
  chartType: ChartType;
}

export interface Widget {
  id: string;
  type: 'chart' | 'kpi' | 'table';
  title: string;
  layout: { i: string, x: number, y: number, w: number, h: number };
  config: ChartConfig;
}

const defaultChartConfig: ChartConfig = { 
  xAxis: null, 
  yAxis: null, 
  color: null, 
  size: null,
  yAggregation: 'sum', 
  filters: [], 
  sortBy: null,
  sortOrder: 'desc',
  limit: null,
  chartType: 'bar' 
};

interface AppState {
  // Global State
  activeDatasetId: string | null;
  setActiveDatasetId: (id: string | null) => void;

  // Datasets
  datasetMetadata: DatasetMetadata | null;
  setDatasetMetadata: (meta: DatasetMetadata | null) => void;

  dashboardName: string;
  setDashboardName: (name: string) => void;

  // History for Undo/Redo
  history: { widgets: Widget[], globalFilters: FilterState[] }[];
  historyIndex: number;
  undo: () => void;
  redo: () => void;
  pushHistory: (widgets: Widget[], globalFilters: FilterState[]) => void;

  // Persistence
  saveDashboard: () => void;
  loadDashboard: (datasetId: string) => boolean;

  // Analysis Results
  dashboardData: any | null;
  setDashboardData: (data: any | null) => void;

  fieldSchema: DatasetFieldSchema | null;
  setFieldSchema: (schema: DatasetFieldSchema | null) => void;

  globalFilters: FilterState[];
  addGlobalFilter: (filter: FilterState) => void;
  updateGlobalFilter: (id: string, updates: Partial<FilterState>) => void;
  removeGlobalFilter: (id: string) => void;

  widgets: Widget[];
  selectedWidgetId: string | null;
  setSelectedWidgetId: (id: string | null) => void;
  addWidget: (type: Widget['type']) => void;
  removeWidget: (id: string) => void;
  updateWidgetLayout: (layouts: any[]) => void;
  updateWidgetConfig: (id: string, config: Partial<ChartConfig>) => void;

  calculatedFields: FieldDescriptor[];
  addCalculatedField: (field: FieldDescriptor) => void;

  profileData: any | null;
  setProfileData: (data: any | null) => void;

  // UI State
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  
  // Resets
  resetState: () => void;
}

export const useDatasetStore = create<AppState>((set) => ({
  activeDatasetId: null,
  setActiveDatasetId: (id) => set({ activeDatasetId: id }),

  datasetMetadata: null,
  setDatasetMetadata: (meta) => set({ datasetMetadata: meta }),

  dashboardName: 'Analytics Dashboard',
  setDashboardName: (name) => set({ dashboardName: name }),

  history: [],
  historyIndex: -1,
  
  pushHistory: (widgets, globalFilters) => set((state) => {
    const newHistory = state.history.slice(0, state.historyIndex + 1);
    newHistory.push({ widgets: JSON.parse(JSON.stringify(widgets)), globalFilters: JSON.parse(JSON.stringify(globalFilters)) });
    return { history: newHistory, historyIndex: newHistory.length - 1 };
  }),

  undo: () => set((state) => {
    if (state.historyIndex > 0) {
      const newIndex = state.historyIndex - 1;
      const snapshot = state.history[newIndex];
      return { 
        historyIndex: newIndex, 
        widgets: JSON.parse(JSON.stringify(snapshot.widgets)), 
        globalFilters: JSON.parse(JSON.stringify(snapshot.globalFilters)) 
      };
    }
    return {};
  }),

  redo: () => set((state) => {
    if (state.historyIndex < state.history.length - 1) {
      const newIndex = state.historyIndex + 1;
      const snapshot = state.history[newIndex];
      return { 
        historyIndex: newIndex, 
        widgets: JSON.parse(JSON.stringify(snapshot.widgets)), 
        globalFilters: JSON.parse(JSON.stringify(snapshot.globalFilters)) 
      };
    }
    return {};
  }),

  saveDashboard: () => {
    const state = useDatasetStore.getState();
    if (!state.activeDatasetId) return;
    const payload = {
      dashboardName: state.dashboardName,
      widgets: state.widgets,
      globalFilters: state.globalFilters,
    };
    localStorage.setItem(`veloce_dashboard_${state.activeDatasetId}`, JSON.stringify(payload));
  },

  loadDashboard: (datasetId: string) => {
    const saved = localStorage.getItem(`veloce_dashboard_${datasetId}`);
    if (saved) {
      try {
        const payload = JSON.parse(saved);
        set({
          dashboardName: payload.dashboardName || 'Analytics Dashboard',
          widgets: payload.widgets || [],
          globalFilters: payload.globalFilters || [],
          history: [{ widgets: payload.widgets || [], globalFilters: payload.globalFilters || [] }],
          historyIndex: 0
        });
        return true;
      } catch (e) {
        console.error("Failed to parse saved dashboard", e);
      }
    }
    return false;
  },

  dashboardData: null,
  setDashboardData: (data) => set({ dashboardData: data }),

  fieldSchema: null,
  setFieldSchema: (schema) => set({ fieldSchema: schema }),

  globalFilters: [],
  addGlobalFilter: (filter) => set((state) => {
    const newFilters = [...state.globalFilters, filter];
    state.pushHistory(state.widgets, newFilters);
    return { globalFilters: newFilters };
  }),
  updateGlobalFilter: (id, updates) => set((state) => {
    const newFilters = state.globalFilters.map(f => f.id === id ? { ...f, ...updates } : f);
    state.pushHistory(state.widgets, newFilters);
    return { globalFilters: newFilters };
  }),
  removeGlobalFilter: (id) => set((state) => {
    const newFilters = state.globalFilters.filter(f => f.id !== id);
    state.pushHistory(state.widgets, newFilters);
    return { globalFilters: newFilters };
  }),

  widgets: [],
  selectedWidgetId: null,
  setSelectedWidgetId: (id) => set({ selectedWidgetId: id }),
  addWidget: (type) => set((state) => {
    const newId = `widget-${Date.now()}`;
    const newWidget: Widget = {
      id: newId,
      type,
      title: `New ${type.charAt(0).toUpperCase() + type.slice(1)}`,
      layout: { i: newId, x: 0, y: Infinity, w: 6, h: 4 },
      config: defaultChartConfig
    };
    const newWidgets = [...state.widgets, newWidget];
    state.pushHistory(newWidgets, state.globalFilters);
    return {
      widgets: newWidgets,
      selectedWidgetId: newId
    };
  }),
  removeWidget: (id) => set((state) => {
    const newWidgets = state.widgets.filter(w => w.id !== id);
    state.pushHistory(newWidgets, state.globalFilters);
    return {
      widgets: newWidgets,
      selectedWidgetId: state.selectedWidgetId === id ? null : state.selectedWidgetId
    };
  }),
  updateWidgetLayout: (layouts) => set((state) => {
    const newWidgets = state.widgets.map(w => {
      const layoutMatch = layouts.find(l => l.i === w.id);
      if (layoutMatch) {
        return { ...w, layout: { ...layoutMatch } };
      }
      return w;
    });
    // We don't push history on every layout tick to avoid spamming the history stack, 
    // unless you want every layout drag to be undoable. Let's push it here.
    state.pushHistory(newWidgets, state.globalFilters);
    return { widgets: newWidgets };
  }),
  updateWidgetConfig: (id, config) => set((state) => {
    const newWidgets = state.widgets.map(w => 
      w.id === id ? { ...w, config: { ...w.config, ...config } } : w
    );
    state.pushHistory(newWidgets, state.globalFilters);
    return { widgets: newWidgets };
  }),

  calculatedFields: [],
  addCalculatedField: (field) => set((state) => ({
    calculatedFields: [...state.calculatedFields, field]
  })),

  profileData: null,
  setProfileData: (data) => set({ profileData: data }),

  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  error: null,
  setError: (error) => set({ error }),

  resetState: () => set({
    activeDatasetId: null,
    datasetMetadata: null,
    dashboardName: 'Analytics Dashboard',
    dashboardData: null,
    fieldSchema: null,
    globalFilters: [],
    widgets: [],
    history: [],
    historyIndex: -1,
    selectedWidgetId: null,
    calculatedFields: [],
    profileData: null,
    error: null,
    isLoading: false,
  }),
}));

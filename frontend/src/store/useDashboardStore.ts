import { create } from 'zustand';
import type { ChartConfig, FilterState } from './useDatasetStore';

export interface Widget {
  id: string;
  type: 'chart' | 'text' | 'image' | 'kpi' | 'shape';
  chartId?: string; // Reference to a saved chart
  content?: string; // For text/image widgets
  title: string;
  description?: string;
  icon?: string;
  isHidden?: boolean;
  layout: { i: string; x: number; y: number; w: number; h: number; minW?: number; minH?: number; maxW?: number; maxH?: number };
  style?: { background?: string; borderRadius?: string; shadow?: string; padding?: string; opacity?: number };
  locked?: boolean;
}

export interface Dashboard {
  id: string;
  datasetId: string;
  name: string;
  description?: string;
  theme: string;
  owner?: string;
  tags?: string[];
  widgets: Widget[];
  filters: FilterState[];
  createdAt: number;
  updatedAt: number;
  isLocked?: boolean;
}

interface DashboardState {
  dashboards: Record<string, Dashboard>; // Keyed by dashboardId
  activeDashboardId: string | null;
  activeWidgetId: string | null;
  savedCharts: Record<string, { id: string; datasetId: string; title: string; config: ChartConfig }>;
  
  // Dashboard Management
  setActiveDashboardId: (id: string | null) => void;
  setActiveWidgetId: (id: string | null) => void;
  createDashboard: (datasetId: string, name: string) => Dashboard;
  updateDashboard: (id: string, updates: Partial<Dashboard>) => void;
  deleteDashboard: (id: string) => void;
  duplicateDashboard: (id: string) => void;
  
  // Widget Management (in active dashboard)
  addWidget: (widget: Omit<Widget, 'id' | 'layout'>) => void;
  updateWidget: (widgetId: string, updates: Partial<Widget>) => void;
  updateWidgetLayout: (layouts: any[]) => void;
  removeWidget: (widgetId: string) => void;
  duplicateWidget: (widgetId: string) => void;

  // Chart Management
  saveChart: (datasetId: string, title: string, config: ChartConfig) => string;
  getChart: (chartId: string) => { id: string; datasetId: string; title: string; config: ChartConfig } | undefined;
  
  // History & Persistence
  history: { past: Record<string, Dashboard>[]; future: Record<string, Dashboard>[] };
  undo: () => void;
  redo: () => void;
  loadState: () => void;
  saveState: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  dashboards: {},
  activeDashboardId: null,
  activeWidgetId: null,
  savedCharts: {},
  history: { past: [], future: [] },

  undo: () => {
    set((state) => {
      if (state.history.past.length === 0) return state;
      const previous = state.history.past[state.history.past.length - 1];
      const newPast = state.history.past.slice(0, -1);
      return {
        dashboards: previous,
        history: { past: newPast, future: [state.dashboards, ...state.history.future] }
      };
    });
    get().saveState();
  },

  redo: () => {
    set((state) => {
      if (state.history.future.length === 0) return state;
      const next = state.history.future[0];
      const newFuture = state.history.future.slice(1);
      return {
        dashboards: next,
        history: { past: [...state.history.past, state.dashboards], future: newFuture }
      };
    });
    get().saveState();
  },

  setActiveDashboardId: (id) => set({ activeDashboardId: id }),
  setActiveWidgetId: (id) => set({ activeWidgetId: id }),

  createDashboard: (datasetId, name) => {
    const id = `dash-${Date.now()}`;
    const newDash: Dashboard = {
      id,
      datasetId,
      name,
      theme: 'dark',
      widgets: [],
      filters: [],
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    set((state) => ({
      dashboards: { ...state.dashboards, [id]: newDash }
    }));
    get().saveState();
    return newDash;
  },

  updateDashboard: (id, updates) => {
    set((state) => {
      const dash = state.dashboards[id];
      if (!dash) return state;
      return {
        dashboards: {
          ...state.dashboards,
          [id]: { ...dash, ...updates, updatedAt: Date.now() }
        },
        history: {
          past: [...state.history.past, state.dashboards].slice(-50), // keep last 50
          future: []
        }
      };
    });
    get().saveState();
  },

  deleteDashboard: (id) => {
    set((state) => {
      const newDashboards = { ...state.dashboards };
      delete newDashboards[id];
      return { dashboards: newDashboards, activeDashboardId: state.activeDashboardId === id ? null : state.activeDashboardId };
    });
    get().saveState();
  },

  duplicateDashboard: (id) => {
    const state = get();
    const source = state.dashboards[id];
    if (source) {
      const newId = `dash-${Date.now()}`;
      set((state) => ({
        dashboards: {
          ...state.dashboards,
          [newId]: { ...source, id: newId, name: `${source.name} (Copy)`, createdAt: Date.now(), updatedAt: Date.now() }
        }
      }));
      get().saveState();
    }
  },

  addWidget: (widgetData) => {
    const state = get();
    const dashId = state.activeDashboardId;
    if (!dashId) return;
    
    const id = `widget-${Date.now()}`;
    const newWidget: Widget = {
      ...widgetData,
      id,
      layout: { i: id, x: 0, y: Infinity, w: 6, h: 4, minW: 2, minH: 2, maxW: 12, maxH: 12 }
    };
    
    const dash = state.dashboards[dashId];
    get().updateDashboard(dashId, { widgets: [...dash.widgets, newWidget] });
  },

  updateWidget: (widgetId, updates) => {
    const state = get();
    const dashId = state.activeDashboardId;
    if (!dashId) return;
    
    const dash = state.dashboards[dashId];
    const widgets = dash.widgets.map(w => w.id === widgetId ? { ...w, ...updates } : w);
    get().updateDashboard(dashId, { widgets });
  },

  updateWidgetLayout: (layouts) => {
    const state = get();
    const dashId = state.activeDashboardId;
    if (!dashId) return;
    
    const dash = state.dashboards[dashId];
    const widgets = dash.widgets.map(w => {
      const layoutMatch = layouts.find(l => l.i === w.id);
      if (layoutMatch) {
        return { ...w, layout: { ...w.layout, ...layoutMatch } };
      }
      return w;
    });
    get().updateDashboard(dashId, { widgets });
  },

  removeWidget: (widgetId) => {
    const state = get();
    const dashId = state.activeDashboardId;
    if (!dashId) return;
    
    const dash = state.dashboards[dashId];
    get().updateDashboard(dashId, { widgets: dash.widgets.filter(w => w.id !== widgetId) });
  },

  duplicateWidget: (widgetId) => {
    const state = get();
    const dashId = state.activeDashboardId;
    if (!dashId) return;

    const dash = state.dashboards[dashId];
    const sourceWidget = dash.widgets.find(w => w.id === widgetId);
    if (!sourceWidget) return;

    const id = `widget-${Date.now()}`;
    const duplicatedWidget: Widget = {
      ...sourceWidget,
      id,
      title: `${sourceWidget.title} (Copy)`,
      layout: { ...sourceWidget.layout, i: id, y: Infinity } // Place at bottom
    };

    get().updateDashboard(dashId, { widgets: [...dash.widgets, duplicatedWidget] });
  },

  saveChart: (datasetId, title, config) => {
    const id = `chart-${Date.now()}`;
    set((state) => ({
      savedCharts: {
        ...state.savedCharts,
        [id]: { id, datasetId, title, config: JSON.parse(JSON.stringify(config)) }
      }
    }));
    get().saveState();
    return id;
  },
  
  getChart: (chartId) => {
    return get().savedCharts[chartId];
  },

  loadState: () => {
    try {
      const data = localStorage.getItem('veloce_dashboard_state');
      if (data) {
        const parsed = JSON.parse(data);
        set({
          dashboards: parsed.dashboards || {},
          savedCharts: parsed.savedCharts || {}
        });
      }
    } catch (e) {
      console.error("Failed to load dashboard state", e);
    }
  },

  saveState: () => {
    try {
      const state = get();
      const dataToSave = {
        dashboards: state.dashboards,
        savedCharts: state.savedCharts
      };
      localStorage.setItem('veloce_dashboard_state', JSON.stringify(dataToSave));
    } catch (e) {
      console.error("Failed to save dashboard state", e);
    }
  }
}));

import React from 'react';
// @ts-ignore
import { Responsive, WidthProvider } from 'react-grid-layout/legacy';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import { useDashboardStore } from '../../store/useDashboardStore';
import type { Widget } from '../../store/useDashboardStore';
import { WidgetContainer } from './WidgetContainer';
import { GridOverlay } from './GridOverlay';
import { LayoutGrid } from 'lucide-react';

const ResponsiveGridLayout = WidthProvider(Responsive);

// Single source of truth for grid geometry, shared with GridOverlay so the
// visual guide lines up exactly with react-grid-layout's own snap positions.
const GRID_BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 };
const GRID_COLS = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 };
const GRID_ROW_HEIGHT = 100;
const GRID_MARGIN: [number, number] = [16, 16];

interface DashboardCanvasProps {
  isLocked?: boolean;
}

export const DashboardCanvas: React.FC<DashboardCanvasProps> = ({ isLocked }) => {
  const { dashboards, activeDashboardId, activeWidgetId, updateWidgetLayout } = useDashboardStore();
  // Mirrors ResponsiveGridLayout's resolved column count for the current
  // breakpoint, fed by its own onBreakpointChange callback below — this is
  // the same value RGL uses internally, so GridOverlay never drifts from it.
  const [gridCols, setGridCols] = React.useState(GRID_COLS.lg);

  if (!activeDashboardId) return null;
  const dashboard = dashboards[activeDashboardId];
  if (!dashboard) return null;

  const handleLayoutChange = (currentLayout: readonly any[]) => {
    updateWidgetLayout(currentLayout as any[]);
  };

  const maxContentRow = dashboard.widgets.reduce(
    (max, w) => Math.max(max, w.layout.y + w.layout.h),
    0
  );

  if (dashboard.widgets.length === 0) {
    return (
      <div className="relative w-full min-h-full">
        {!isLocked && (
          <GridOverlay
            cols={gridCols}
            rowHeight={GRID_ROW_HEIGHT}
            margin={GRID_MARGIN}
          />
        )}
        <div className="absolute inset-0 flex items-center justify-center flex-col text-gray-500 z-10">
          <div className="w-24 h-24 border-2 border-dashed border-dark-700 rounded-xl mb-4 flex items-center justify-center bg-dark-800/50">
            <LayoutGrid className="w-10 h-10 text-dark-500" />
          </div>
          <h3 className="text-xl font-medium text-white mb-2">Empty Canvas</h3>
          <p className="text-sm max-w-sm text-center">
            Go back to the Chart Builder to create visual charts, or use the Add Widget button above to add text and KPI cards.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full min-h-full transition-colors duration-300">
      {!isLocked && (
        <GridOverlay
          cols={gridCols}
          rowHeight={GRID_ROW_HEIGHT}
          margin={GRID_MARGIN}
          contentRows={maxContentRow}
        />
      )}
      <style>{`
        .react-grid-item {
          transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1), width 200ms cubic-bezier(0.4, 0, 0.2, 1), height 200ms cubic-bezier(0.4, 0, 0.2, 1) !important;
          will-change: transform, width, height;
        }
        .react-grid-item.react-draggable-dragging {
          transition: none !important;
          z-index: 100 !important;
        }
        .react-grid-item.react-resizable-resizing {
          transition: none !important;
          z-index: 100 !important;
        }
        .react-grid-item.react-grid-placeholder {
          background: rgba(14, 165, 233, 0.15) !important;
          border: 2px dashed rgba(14, 165, 233, 0.5) !important;
          border-radius: 0.75rem !important;
          opacity: 1 !important;
          transition-duration: 150ms !important;
          z-index: 0;
        }
      `}</style>
      <ResponsiveGridLayout
        className="layout relative z-10"
        layouts={{ lg: dashboard.widgets.map((w: Widget) => ({
          ...w.layout,
          minW: w.layout.minW ?? 2,
          minH: w.layout.minH ?? 2,
          maxW: w.layout.maxW ?? 12,
          maxH: w.layout.maxH ?? 12,
          static: w.locked || false
        })) }}
        breakpoints={GRID_BREAKPOINTS}
        cols={GRID_COLS}
        rowHeight={GRID_ROW_HEIGHT}
        onLayoutChange={handleLayoutChange}
        onBreakpointChange={(_breakpoint: string, newCols: number) => setGridCols(newCols)}
        draggableHandle=".widget-drag-handle"
        margin={GRID_MARGIN}
        isDraggable={!isLocked}
        isResizable={!isLocked}
        resizeHandles={['s', 'w', 'e', 'n', 'sw', 'nw', 'se', 'ne']}
      >
        {dashboard.widgets.map((widget: Widget) => {
          const isActive = widget.id === activeWidgetId;
          return (
            <div 
              key={widget.id} 
              className={`relative group rounded-xl shadow-lg bg-dark-800 transition-colors ${isActive && !isLocked ? 'ring-2 ring-brand-500' : 'border border-dark-700 hover:border-dark-500'}`}
            >
              <WidgetContainer widget={widget} isLocked={isLocked} />
            </div>
          );
        })}
      </ResponsiveGridLayout>
    </div>
  );
};

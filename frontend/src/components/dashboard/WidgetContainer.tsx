import React from 'react';
import type { Widget as DashboardWidget } from '../../store/useDashboardStore';
import { useDashboardStore } from '../../store/useDashboardStore';

import { WidgetRenderer } from '../WidgetRenderer';
import { Maximize2, Minimize2, Copy, GripHorizontal, Trash2, Eye, EyeOff, Lock, Unlock } from 'lucide-react';

interface WidgetContainerProps {
  widget: DashboardWidget;
  isLocked?: boolean;
}

export const WidgetContainer: React.FC<WidgetContainerProps> = ({ widget, isLocked }) => {
  const { savedCharts, removeWidget, duplicateWidget, updateWidget } = useDashboardStore();

  let content = null;

  if (widget.type === 'chart' && widget.chartId) {
    const savedChart = savedCharts[widget.chartId];
    if (savedChart) {
      // Mock the useDatasetStore Widget interface that WidgetRenderer expects
      const datasetWidget = {
        id: widget.id,
        type: 'chart' as const,
        title: widget.title,
        config: savedChart.config,
        layout: widget.layout
      };
      // @ts-ignore
      content = <WidgetRenderer datasetId={savedChart.datasetId} widget={datasetWidget} />;
    } else {
      content = <div className="p-4 text-red-400">Chart not found</div>;
    }
  } else if (widget.type === 'text') {
    content = <div className="p-4 text-white h-full overflow-auto prose prose-invert">{widget.content}</div>;
  } else if (widget.type === 'kpi') {
    content = <div className="p-4 text-white flex items-center justify-center h-full text-4xl font-bold">{widget.content}</div>;
  } else {
    content = <div className="p-4 text-gray-500">Unknown widget type</div>;
  }

  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const [editTitle, setEditTitle] = React.useState(widget.title);

  React.useEffect(() => {
    const handleRename = (e: CustomEvent) => {
      if (e.detail.id === widget.id && !isLocked) {
        setIsEditing(true);
      }
    };
    window.addEventListener('veloce-rename-widget', handleRename as EventListener);
    return () => window.removeEventListener('veloce-rename-widget', handleRename as EventListener);
  }, [widget.id, isLocked]);

  const handleSaveTitle = () => {
    if (editTitle.trim() !== '') {
      updateWidget(widget.id, { title: editTitle });
    } else {
      setEditTitle(widget.title);
    }
    setIsEditing(false);
  };

  const toolbar = !isLocked && (
    <div className="h-8 border-b border-dark-700 bg-dark-900/80 flex items-center justify-between px-2 opacity-0 group-hover:opacity-100 transition-opacity absolute top-0 left-0 right-0 z-20 widget-drag-handle cursor-move">
      <div className="flex items-center gap-2 flex-1 min-w-0 pr-2">
        <GripHorizontal className="w-4 h-4 text-gray-500 shrink-0" />
        {isEditing ? (
          <div className="flex items-center flex-1" onPointerDown={(e) => e.stopPropagation()}>
            <input 
              autoFocus
              type="text" 
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveTitle();
                if (e.key === 'Escape') {
                  setEditTitle(widget.title);
                  setIsEditing(false);
                }
              }}
              onBlur={handleSaveTitle}
              className="text-xs font-medium text-white bg-dark-800 border border-brand-500 rounded px-1.5 py-0.5 outline-none w-full"
            />
          </div>
        ) : (
          <span 
            className="text-xs font-medium text-gray-300 truncate max-w-full hover:text-white cursor-text"
            onDoubleClick={(e) => {
              e.stopPropagation();
              setIsEditing(true);
            }}
            title="Double click to rename"
          >
            {widget.title}
          </span>
        )}
      </div>
      <div className="flex items-center gap-1 shrink-0 bg-dark-900 pl-1" onPointerDown={(e) => e.stopPropagation()}>
        <button onClick={() => updateWidget(widget.id, { locked: !widget.locked })} className={`p-1 rounded transition-colors ${widget.locked ? 'bg-amber-500/20 text-amber-400' : 'hover:bg-dark-700 text-gray-400 hover:text-white'}`} title={widget.locked ? "Unlock Position" : "Lock Position"}>
          {widget.locked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
        </button>
        <button onClick={() => updateWidget(widget.id, { isHidden: !widget.isHidden })} className="p-1 hover:bg-dark-700 text-gray-400 hover:text-white rounded transition-colors" title={widget.isHidden ? "Show" : "Hide"}>
          {widget.isHidden ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
        </button>
        <button onClick={() => setIsFullscreen(true)} className="p-1 hover:bg-dark-700 text-gray-400 hover:text-white rounded transition-colors" title="Fullscreen">
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => duplicateWidget(widget.id)} className="p-1 hover:bg-dark-700 text-gray-400 hover:text-white rounded transition-colors" title="Duplicate">
          <Copy className="w-3.5 h-3.5" />
        </button>
        <button 
          className="p-1 hover:bg-red-500/20 text-gray-400 hover:text-red-400 rounded transition-colors" 
          title="Remove"
          onClick={() => removeWidget(widget.id)}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );

  if (isLocked && widget.isHidden) {
    return <div className="hidden" />;
  }

  const widgetBody = (
    <div 
      className={`w-full h-full flex flex-col transition-all overflow-hidden ${isFullscreen ? 'bg-dark-800 p-4' : ''} ${widget.isHidden ? 'opacity-50 grayscale' : ''}`}
      onClick={(e) => {
        if (!isLocked) {
          e.stopPropagation();
          useDashboardStore.getState().setActiveWidgetId(widget.id);
        }
      }}
      style={{
        backgroundColor: widget.style?.background || undefined,
        borderRadius: widget.style?.borderRadius || undefined,
        opacity: widget.style?.opacity ?? 1,
      }}
    >
      {toolbar}
      <div className={`flex-1 w-full h-full ${!isLocked ? 'pt-8' : ''}`}>
        {widget.isHidden && !isLocked ? (
          <div className="w-full h-full flex items-center justify-center text-gray-500">
            <EyeOff className="w-8 h-8 opacity-20" />
          </div>
        ) : content}
      </div>
      {isFullscreen && (
        <button 
          onClick={() => setIsFullscreen(false)} 
          className="absolute top-4 right-4 p-2 bg-dark-700 hover:bg-dark-600 rounded-lg text-white shadow-lg transition-colors z-50 flex items-center gap-2"
        >
          <Minimize2 className="w-4 h-4" /> Close Fullscreen
        </button>
      )}
    </div>
  );

  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-dark-950/90 backdrop-blur-sm p-8 flex items-center justify-center animate-in fade-in zoom-in-95 duration-200">
        <div className="w-full h-full max-w-7xl max-h-[90vh] bg-dark-800 rounded-2xl shadow-2xl border border-dark-700 overflow-hidden relative">
          {widgetBody}
        </div>
      </div>
    );
  }

  return widgetBody;
};

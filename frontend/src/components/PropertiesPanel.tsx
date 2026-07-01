import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { useDatasetStore } from '../store/useDatasetStore';
import type { ChartConfig, FilterState } from '../store/useDatasetStore';
import { X, Filter } from 'lucide-react';
import type { FieldDescriptor } from '../api/datasets';
import { useDashboardStore } from '../store/useDashboardStore';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

interface DropZoneProps {
  id: string;
  label: string;
  field: FieldDescriptor | null;
  onRemove: () => void;
  aggregation?: string;
  onAggregationChange?: (agg: string) => void;
}

const DropZone: React.FC<DropZoneProps> = ({ id, label, field, onRemove, aggregation, onAggregationChange }) => {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</label>
      <div 
        ref={setNodeRef}
        className={`min-h-[48px] border-2 border-dashed rounded-xl flex items-center px-3 transition-all duration-300 ${
          isOver ? 'border-brand-500 bg-brand-500/20 shadow-glow-brand scale-[1.02]' : 'border-dark-600 bg-dark-800/80 hover:border-dark-500 hover:bg-dark-800'
        }`}
      >
        {field ? (
          <div className="flex items-center gap-2 bg-brand-500/20 text-brand-300 border border-brand-500/30 px-3 py-1 rounded-md text-sm font-medium w-full">
            <span className="truncate flex-1">{field.field}</span>
            {onAggregationChange && (
              <select 
                value={aggregation} 
                onChange={(e) => onAggregationChange(e.target.value)}
                className="bg-dark-900 border border-dark-600 text-xs rounded px-1 py-0.5 outline-none cursor-pointer"
              >
                <option value="sum">Sum</option>
                <option value="mean">Average</option>
                <option value="min">Min</option>
                <option value="max">Max</option>
                <option value="count">Count</option>
              </select>
            )}
            <button onClick={onRemove} className="hover:bg-brand-500/30 rounded p-0.5 transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <span className="text-sm text-gray-500 italic">Drop field here...</span>
        )}
      </div>
    </div>
  );
};

const FilterItemControl: React.FC<{
  filter: FilterState;
  onUpdate: (f: FilterState) => void;
  onRemove: () => void;
}> = ({ filter, onUpdate, onRemove }) => {
  const isNumeric = filter.field.dataType === 'integer' || filter.field.dataType === 'float';

  return (
    <div className="flex flex-col gap-1 bg-dark-900 border border-dark-600 rounded-md p-2 w-full">
      <div className="flex justify-between items-center w-full">
        <span className="text-sm font-medium text-brand-300 truncate">{filter.field.field}</span>
        <button onClick={onRemove} className="text-gray-500 hover:text-red-400 p-0.5 rounded transition-colors">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="flex gap-2">
        <select
          value={filter.operator}
          onChange={(e) => onUpdate({ ...filter, operator: e.target.value })}
          className="bg-dark-800 border border-dark-600 text-xs text-gray-200 rounded px-1 py-1 outline-none cursor-pointer flex-1"
        >
          <option value="eq">=</option>
          <option value="neq">!=</option>
          {isNumeric ? (
            <>
              <option value="gt">&gt;</option>
              <option value="gte">&gt;=</option>
              <option value="lt">&lt;</option>
              <option value="lte">&lt;=</option>
            </>
          ) : (
            <>
              <option value="contains">contains</option>
              <option value="in">in list (comma sep)</option>
              <option value="not_in">not in list</option>
            </>
          )}
        </select>
        <input
          type={isNumeric ? "number" : "text"}
          defaultValue={filter.value}
          onBlur={(e) => {
            const val = e.target.value;
            if (val !== filter.value) {
              onUpdate({ ...filter, value: val });
            }
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.currentTarget.blur();
            }
          }}
          className="bg-dark-800 border border-dark-600 text-xs text-white rounded px-2 py-1 outline-none focus:border-brand-500 flex-1 min-w-0"
          placeholder="Value..."
        />
      </div>
    </div>
  );
};

const FilterDropZone: React.FC<{
  filters: FilterState[];
  onUpdate: (idx: number, f: FilterState) => void;
  onRemove: (idx: number) => void;
}> = ({ filters, onUpdate, onRemove }) => {
  const { setNodeRef, isOver } = useDroppable({ id: 'filters' });

  return (
    <div className="flex flex-col gap-1.5 w-full mt-4">
      <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
        <Filter className="w-3 h-3" /> Filters
      </label>
      <div 
        ref={setNodeRef}
        className={`min-h-[48px] border-2 border-dashed rounded-xl flex flex-col p-2 gap-2 transition-all duration-300 ${
          isOver ? 'border-brand-500 bg-brand-500/20 shadow-glow-brand scale-[1.02]' : 'border-dark-600 bg-dark-800/80 hover:border-dark-500 hover:bg-dark-800'
        }`}
      >
        {filters.length === 0 && (
          <span className="text-sm text-gray-500 italic px-1 py-2 text-center">Drop fields here</span>
        )}
        {filters.map((f, idx) => (
          <FilterItemControl 
            key={f.id} 
            filter={f} 
            onUpdate={(updated) => onUpdate(idx, updated)}
            onRemove={() => onRemove(idx)}
          />
        ))}
      </div>
    </div>
  );
};

export const PropertiesPanel: React.FC = () => {
  const { widgets, selectedWidgetId, updateWidgetConfig, removeWidget } = useDatasetStore();
  const navigate = useNavigate();
  const { datasetId } = useParams<{ datasetId: string }>();
  
  const selectedWidget = widgets.find(w => w.id === selectedWidgetId);

  if (!selectedWidget) {
    return (
      <div className="w-80 flex-shrink-0 bg-dark-800/60 backdrop-blur-md border-l border-dark-700/50 p-6 flex flex-col items-center justify-center text-gray-500 h-[calc(100vh-64px)]">
        <div className="w-16 h-16 border-2 border-dashed border-gray-600 rounded-2xl mb-4 opacity-50"></div>
        <p className="text-center text-sm font-medium">Select a widget on the canvas to edit its properties</p>
      </div>
    );
  }

  const chartConfig = selectedWidget.config;
  const setChartConfig = (config: Partial<ChartConfig>) => {
    updateWidgetConfig(selectedWidgetId!, config);
  };

  const chartType = chartConfig.chartType;

  // Dynamic DropZone configuration based on chartType
  let xLabel = "X-Axis";
  let yLabel = "Y-Axis";
  let showColor = true;
  let showSize = false;
  let colorLabel = "Color Split";
  
  if (['pie', 'doughnut', 'treemap', 'funnel'].includes(chartType)) {
    xLabel = "Category";
    yLabel = "Value";
    showColor = false;
  } else if (['scatter'].includes(chartType)) {
    xLabel = "X-Axis (Measure)";
    yLabel = "Y-Axis (Measure)";
  } else if (['bubble'].includes(chartType)) {
    xLabel = "X-Axis (Measure)";
    yLabel = "Y-Axis (Measure)";
    showSize = true;
  } else if (['heatmap'].includes(chartType)) {
    xLabel = "X-Axis (Dimension)";
    yLabel = "Y-Axis (Dimension)";
    colorLabel = "Value (Measure)";
  } else if (['table', 'pivotTable'].includes(chartType)) {
    xLabel = "Rows / Dimensions";
    yLabel = "Values / Measures";
    showColor = false;
  } else if (['kpi', 'metric', 'gauge'].includes(chartType)) {
    xLabel = "Category (Optional)";
    yLabel = "Value (Measure)";
    showColor = false;
  }

  return (
    <div className="w-80 flex-shrink-0 bg-dark-800/60 backdrop-blur-md border-l border-dark-700/50 flex flex-col h-[calc(100vh-64px)] overflow-y-auto custom-scrollbar">
      <div className="p-4 border-b border-dark-700/50 bg-dark-900/30 sticky top-0 z-10 flex justify-between items-center backdrop-blur-md">
        <div>
          <h3 className="font-semibold text-white">Properties</h3>
          <p className="text-xs text-gray-400">{selectedWidget.title}</p>
        </div>
        <div className="flex items-center gap-1">
          <button 
            onClick={() => {
              const { saveChart } = useDashboardStore.getState();
              saveChart(datasetId!, selectedWidget.title, selectedWidget.config);
              
              // If there's an active dashboard, or we can just redirect to dashboard manager
              navigate(`/dataset/${datasetId}/dashboards`);
            }}
            className="text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white px-2 py-1 rounded transition-colors flex items-center gap-1"
            title="Save to Dashboard"
          >
            Save <ArrowRight className="w-3 h-3" />
          </button>
          <button 
            onClick={() => removeWidget(selectedWidget.id)}
            className="text-red-400 hover:text-red-300 hover:bg-red-400/10 p-1.5 rounded-md transition-colors"
            title="Delete Widget"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 flex flex-col gap-4">
        {/* Type Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Chart Type</label>
          <select 
            value={chartConfig.chartType}
            onChange={(e) => setChartConfig({ chartType: e.target.value as any })}
            className="w-full bg-dark-900 border border-dark-600 text-sm text-white rounded-lg px-3 py-2 outline-none focus:border-brand-500"
          >
            <optgroup label="Comparison">
              <option value="bar">Bar Chart</option>
              <option value="column">Column Chart</option>
              <option value="horizontalBar">Horizontal Bar</option>
              <option value="groupedBar">Grouped Bar</option>
              <option value="stackedBar">Stacked Bar</option>
            </optgroup>
            <optgroup label="Trend">
              <option value="line">Line Chart</option>
              <option value="area">Area Chart</option>
              <option value="spline">Spline Chart</option>
            </optgroup>
            <optgroup label="Distribution">
              <option value="histogram">Histogram</option>
              <option value="boxplot">Box Plot</option>
            </optgroup>
            <optgroup label="Composition">
              <option value="pie">Pie Chart</option>
              <option value="doughnut">Doughnut Chart</option>
              <option value="treemap">Treemap</option>
            </optgroup>
            <optgroup label="Relationship">
              <option value="scatter">Scatter Plot</option>
              <option value="bubble">Bubble Chart</option>
            </optgroup>
            <optgroup label="Advanced">
              <option value="heatmap">Heatmap</option>
              <option value="radar">Radar Chart</option>
              <option value="waterfall">Waterfall Chart</option>
              <option value="funnel">Funnel Chart</option>
              <option value="gauge">Gauge</option>
            </optgroup>
            <optgroup label="Tabular">
              <option value="table">Data Table</option>
              <option value="pivotTable">Pivot Table</option>
            </optgroup>
            <optgroup label="KPI">
              <option value="kpi">KPI Card</option>
              <option value="metric">Metric Card</option>
            </optgroup>
          </select>
        </div>

        <hr className="border-dark-700 my-2" />

        <DropZone 
          id="xAxis" 
          label={xLabel} 
          field={chartConfig.xAxis} 
          onRemove={() => setChartConfig({ xAxis: null })} 
        />
        
        <DropZone 
          id="yAxis" 
          label={yLabel}
          field={chartConfig.yAxis} 
          onRemove={() => setChartConfig({ yAxis: null })} 
          aggregation={chartConfig.yAggregation}
          onAggregationChange={(agg) => setChartConfig({ yAggregation: agg })}
        />
        
        {showColor && (
          <DropZone 
            id="color" 
            label={colorLabel}
            field={chartConfig.color} 
            onRemove={() => setChartConfig({ color: null })} 
          />
        )}

        {showSize && (
          <DropZone 
            id="size" 
            label="Size (Measure)"
            field={chartConfig.size} 
            onRemove={() => setChartConfig({ size: null })} 
          />
        )}

        <hr className="border-dark-700 my-2" />

        <FilterDropZone 
          filters={chartConfig.filters}
          onUpdate={(idx, updated) => {
            const newFilters = [...chartConfig.filters];
            newFilters[idx] = updated;
            setChartConfig({ filters: newFilters });
          }}
          onRemove={(idx) => {
            const newFilters = [...chartConfig.filters];
            newFilters.splice(idx, 1);
            setChartConfig({ filters: newFilters });
          }}
        />

        <hr className="border-dark-700 my-2" />

        <div className="flex flex-col gap-1.5 w-full">
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Sorting & Limits</label>
          
          <div className="flex gap-2 mb-2">
            <select 
              value={chartConfig.sortBy || ''}
              onChange={(e) => setChartConfig({ sortBy: e.target.value || null })}
              className="bg-dark-900 border border-dark-600 text-xs text-gray-200 rounded px-2 py-1.5 outline-none flex-1"
            >
              <option value="">Default Sort</option>
              {chartConfig.xAxis && <option value={chartConfig.xAxis.field}>By {xLabel}</option>}
              {chartConfig.yAxis && <option value={chartConfig.yAxis.field}>By {yLabel}</option>}
            </select>

            {chartConfig.sortBy && (
              <select 
                value={chartConfig.sortOrder || 'desc'}
                onChange={(e) => setChartConfig({ sortOrder: e.target.value as any })}
                className="bg-dark-900 border border-dark-600 text-xs text-gray-200 rounded px-2 py-1.5 outline-none w-20"
              >
                <option value="asc">Asc</option>
                <option value="desc">Desc</option>
              </select>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 w-16">Top/Limit:</span>
            <input 
              type="number" 
              placeholder="All"
              value={chartConfig.limit || ''}
              onChange={(e) => setChartConfig({ limit: e.target.value ? Number(e.target.value) : null })}
              className="bg-dark-900 border border-dark-600 text-xs text-white rounded px-2 py-1.5 outline-none focus:border-brand-500 w-full"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

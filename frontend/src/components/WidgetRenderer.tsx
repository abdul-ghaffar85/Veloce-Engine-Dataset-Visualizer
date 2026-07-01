import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { aggregationsApi } from '../api/aggregations';
import { ChartRenderer } from './ChartRenderer';
import { Loader2, BarChart3 } from 'lucide-react';
import { useDatasetStore } from '../store/useDatasetStore';
import type { Widget } from '../store/useDatasetStore';

const CHART_COLORS = [
  '#14b8a6', // Teal 500
  '#0ea5e9', // Sky 500
  '#8b5cf6', // Violet 500
  '#f43f5e', // Rose 500
  '#f59e0b', // Amber 500
  '#10b981', // Emerald 500
  '#6366f1', // Indigo 500
  '#ec4899', // Pink 500
  '#84cc16', // Lime 500
  '#06b6d4'  // Cyan 500
];

interface WidgetRendererProps {
  datasetId: string;
  widget: Widget;
}

export const WidgetRenderer: React.FC<WidgetRendererProps> = ({ datasetId, widget }) => {
  const chartConfig = widget.config;
  const isReady = chartConfig.xAxis && chartConfig.yAxis;

  // Construct the query based on the dropped fields
  const { data: queryResult, isLoading, error } = useQuery({
    queryKey: ['aggregation', datasetId, chartConfig.xAxis?.field, chartConfig.yAxis?.field, chartConfig.color?.field, chartConfig.size?.field, chartConfig.yAggregation, chartConfig.filters],
    queryFn: async () => {
      if (!isReady && !['kpi', 'metric'].includes(chartConfig.chartType)) return null;
      if (['kpi', 'metric'].includes(chartConfig.chartType) && !chartConfig.yAxis) return null;
      
      const x = chartConfig.xAxis;
      const y = chartConfig.yAxis!;
      const c = chartConfig.color;
      const s = chartConfig.size;
      
      const group_by: string[] = [];
      if (x && x.semanticType === 'dimension') group_by.push(x.field);
      if (c && c.semanticType === 'dimension') group_by.push(c.field);

      const aggregates = [
        {
          column: y.field,
          function: chartConfig.yAggregation || y.defaultAggregation || 'sum'
        }
      ];

      if (x && x.semanticType === 'metric') {
        aggregates.push({ column: x.field, function: x.defaultAggregation || 'sum' });
      }
      if (s && s.semanticType === 'metric') {
        aggregates.push({ column: s.field, function: s.defaultAggregation || 'sum' });
      }
      if (c && c.semanticType === 'metric') {
        aggregates.push({ column: c.field, function: c.defaultAggregation || 'sum' });
      }

      const { globalFilters } = useDatasetStore.getState();

      const combinedFilters = [
        ...chartConfig.filters,
        ...globalFilters
      ];

      const query: any = {
        filters: combinedFilters
          .filter(f => f.value.toString().trim() !== '')
          .map(f => {
            let val: any = f.value;
            if (f.operator === 'in' || f.operator === 'not_in') {
              val = val.toString().split(',').map((v: string) => v.trim());
            } else if (f.field.dataType === 'integer' || f.field.dataType === 'float') {
              val = Number(val);
            }
            return {
              column: f.field.field,
              operator: f.operator,
              value: val
            };
          }),
        group_by,
        aggregates,
        limit: chartConfig.limit || ((c || s) ? 1000 : 100),
        chartType: chartConfig.chartType,
        xAxis: chartConfig.xAxis?.field || null,
        yAxis: chartConfig.yAxis?.field || null,
        aggregation: chartConfig.yAggregation || 'sum'
      };

      if (chartConfig.sortBy) {
        query.sort = [{ column: chartConfig.sortBy, order: chartConfig.sortOrder || 'desc' }];
      }
      
      return aggregationsApi.executeQuery(datasetId, query);
    },
    enabled: !!isReady || (['kpi', 'metric'].includes(chartConfig.chartType) && !!chartConfig.yAxis),
  });

  // Transform backend aggregation data into Chart.js config
  const chartData = React.useMemo(() => {
    if (!queryResult || !queryResult.data) return null;

    const xField = chartConfig.xAxis?.field;
    const yField = chartConfig.yAxis?.field;
    const cField = chartConfig.color?.field;
    const sField = chartConfig.size?.field;
    
    // For KPI
    if (['kpi', 'metric'].includes(chartConfig.chartType)) {
       return {
         type: chartConfig.chartType,
         value: queryResult.data[0]?.[yField!] || 0,
         label: yField
       };
    }

    if (!xField || !yField) return null;

    const firstRow = queryResult.data[0];
    if (!firstRow) return null;

    let labels: string[] = [];
    let datasets: any[] = [];

    const isScatter = ['scatter', 'bubble'].includes(chartConfig.chartType);
    
    if (isScatter) {
      // Scatter & Bubble
      if (!cField) {
        datasets = [{
          label: 'Data',
          data: queryResult.data.map(row => ({
            x: Number(row[xField] || 0),
            y: Number(row[yField] || 0),
            r: sField ? Number(row[sField] || 5) : 5
          })),
          backgroundColor: 'rgba(34, 197, 94, 0.5)',
          borderColor: '#22c55e',
        }];
      } else {
        const colorGroups = new Map<string, any[]>();
        queryResult.data.forEach(row => {
          const cVal = String(row[cField] ?? 'null');
          if (!colorGroups.has(cVal)) colorGroups.set(cVal, []);
          colorGroups.get(cVal)!.push({
            x: Number(row[xField] || 0),
            y: Number(row[yField] || 0),
            r: sField ? Number(row[sField] || 5) : 5
          });
        });
        let colorIndex = 0;
        colorGroups.forEach((data, cVal) => {
          const colorHex = CHART_COLORS[colorIndex % CHART_COLORS.length];
          datasets.push({
            label: cVal,
            data,
            backgroundColor: `${colorHex}80`,
            borderColor: colorHex,
          });
          colorIndex++;
        });
      }
    } else if (['pie', 'doughnut', 'radar', 'treemap'].includes(chartConfig.chartType)) {
      // 1D Array for pie/doughnut/radar
      labels = queryResult.data.map(row => String(row[xField] ?? 'null'));
      const data = queryResult.data.map(row => Number(row[yField] || 0));
      datasets = [{
        label: yField,
        data,
        backgroundColor: CHART_COLORS.map(c => `${c}CC`),
        borderColor: '#1f2937',
        borderWidth: 2,
      }];
    } else {
      // Standard Bar/Line 1D or 2D (Pivot)
      if (!cField) {
        labels = queryResult.data.map(row => String(row[xField] ?? 'null'));
        datasets = [{
          label: yField,
          data: queryResult.data.map(row => Number(row[yField] || 0)),
          backgroundColor: 'rgba(34, 197, 94, 0.2)',
          borderColor: '#22c55e',
        }];
      } else {
        const labelSet = new Set<string>();
        const colorGroups = new Map<string, Map<string, number>>();

        queryResult.data.forEach(row => {
          const xVal = String(row[xField] ?? 'null');
          const cVal = String(row[cField] ?? 'null');
          const yVal = Number(row[yField] || 0);

          labelSet.add(xVal);
          if (!colorGroups.has(cVal)) colorGroups.set(cVal, new Map());
          colorGroups.get(cVal)!.set(xVal, yVal);
        });

        labels = Array.from(labelSet);
        let colorIndex = 0;
        colorGroups.forEach((valuesMap, cVal) => {
          const colorHex = CHART_COLORS[colorIndex % CHART_COLORS.length];
          datasets.push({
            label: cVal,
            data: labels.map(l => valuesMap.get(l) || 0),
            backgroundColor: `${colorHex}33`,
            borderColor: colorHex,
          });
          colorIndex++;
        });
      }
    }

    return {
      type: chartConfig.chartType,
      labels,
      datasets
    };
  }, [queryResult, chartConfig]);

  return (
    <div className="w-full h-full flex flex-col bg-dark-800 border border-dark-700 rounded-lg overflow-hidden shadow-sm">
      {/* Widget Header */}
      <div className="px-3 py-2 border-b border-dark-700 flex justify-between items-center bg-dark-900/50">
        <h4 className="text-sm font-semibold text-gray-200">{widget.title}</h4>
      </div>
      
      {/* Widget Content */}
      <div className="flex-1 relative p-2">
        {!isReady && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500">
            <BarChart3 className="w-8 h-8 opacity-30 mb-2" />
            <p className="text-xs text-center px-4">Select this widget and drop fields into the Properties Panel</p>
          </div>
        )}

        {isReady && isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-dark-900/80 backdrop-blur-sm z-10">
            <Loader2 className="w-6 h-6 text-brand-500 animate-spin mb-2" />
          </div>
        )}

        {isReady && error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400 bg-red-950/10 z-10 p-4 text-center">
            <p className="text-xs opacity-80">{error.message}</p>
          </div>
        )}

        {isReady && chartData && (
          <div className="w-full h-full">
            <ChartRenderer config={chartData} />
          </div>
        )}
      </div>
    </div>
  );
};

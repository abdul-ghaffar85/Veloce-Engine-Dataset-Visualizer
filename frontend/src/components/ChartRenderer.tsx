import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Pie, Doughnut, Radar, Scatter, Bubble } from 'react-chartjs-2';

// Import new specialized plugins
import { TreemapController, TreemapElement } from 'chartjs-chart-treemap';
import { BoxPlotController, BoxAndWiskers } from '@sgratzl/chartjs-chart-boxplot';
import { MatrixController, MatrixElement } from 'chartjs-chart-matrix';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
  TreemapController,
  TreemapElement,
  BoxPlotController,
  BoxAndWiskers,
  MatrixController,
  MatrixElement
);

interface ChartRendererProps {
  config: any; // Dynamic config based on chart type
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({ config }) => {
  if (['kpi', 'metric'].includes(config.type)) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4">
        <h4 className="text-gray-400 text-sm font-medium uppercase tracking-wider mb-2">{config.label}</h4>
        <div className="text-4xl font-bold text-white tracking-tight">
          {Number(config.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </div>
      </div>
    );
  }

  const baseOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        display: !['treemap', 'histogram', 'boxplot'].includes(config.type),
        labels: {
          color: '#a1a1aa', // text-zinc-400
          font: { family: 'Inter', size: 12, weight: 500 },
          usePointStyle: true,
          boxWidth: 8,
        }
      },
      tooltip: {
        backgroundColor: 'rgba(24, 24, 27, 0.85)', // backdrop-blur compatible
        titleColor: '#f4f4f5',
        bodyColor: '#e4e4e7',
        borderColor: '#3f3f46',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        titleFont: { family: 'Outfit', size: 14, weight: 600 },
        bodyFont: { family: 'Inter', size: 13 },
        displayColors: true,
        boxPadding: 4,
      }
    },
  };

  const axisOptions = {
    scales: {
      x: {
        grid: { color: 'rgba(63, 63, 70, 0.3)', tickLength: 0, drawBorder: false },
        ticks: { color: '#71717a', font: { family: 'Inter', size: 11 }, padding: 8 },
        stacked: config.type === 'stackedBar',
        border: { display: false }
      },
      y: {
        grid: { color: 'rgba(63, 63, 70, 0.3)', tickLength: 0, drawBorder: false },
        ticks: { color: '#71717a', font: { family: 'Inter', size: 11 }, padding: 8 },
        stacked: config.type === 'stackedBar',
        border: { display: false }
      }
    }
  };

  const isRadial = ['pie', 'doughnut', 'radar', 'gauge'].includes(config.type);
  const options = isRadial ? baseOptions : { ...baseOptions, ...axisOptions };

  // Gauge-specific overrides
  if (config.type === 'gauge') {
    options.rotation = -90;
    options.circumference = 180;
  }

  // Horizontal Bar
  if (config.type === 'horizontalBar') {
    options.indexAxis = 'y';
  }

  // Ensure default brand colors and formats if not provided
  const processedData = {
    labels: config.labels,
    datasets: config.datasets?.map((ds: any, i: number) => ({
      ...ds,
      backgroundColor: ds.backgroundColor || (i === 0 ? 'rgba(20, 184, 166, 0.25)' : 'rgba(14, 165, 233, 0.25)'),
      borderColor: ds.borderColor || (i === 0 ? '#14b8a6' : '#0ea5e9'),
      borderWidth: 2,
      tension: config.type === 'spline' ? 0.4 : 0,
      fill: config.type === 'area',
      pointBackgroundColor: ds.borderColor || (i === 0 ? '#14b8a6' : '#0ea5e9'),
      borderRadius: ['bar', 'column', 'horizontalBar', 'groupedBar', 'stackedBar', 'histogram', 'waterfall'].includes(config.type) ? 4 : 0,
    }))
  };

  return (
    <div className="h-64 w-full">
      {['line', 'area', 'spline'].includes(config.type) && <Line options={options} data={processedData} />}
      {['bar', 'column', 'horizontalBar', 'groupedBar', 'stackedBar', 'histogram', 'waterfall'].includes(config.type) && <Bar options={options} data={processedData} />}
      {config.type === 'pie' && <Pie options={options} data={processedData} />}
      {['doughnut', 'gauge'].includes(config.type) && <Doughnut options={options} data={processedData} />}
      {config.type === 'radar' && <Radar options={options} data={processedData} />}
      {config.type === 'scatter' && <Scatter options={options} data={processedData} />}
      {config.type === 'bubble' && <Bubble options={options} data={processedData} />}
      
      {['treemap', 'boxplot', 'heatmap', 'funnel', 'table', 'pivotTable'].includes(config.type) && (
        <div className="h-full flex flex-col items-center justify-center text-gray-400 text-sm p-4 text-center">
          <div className="bg-dark-700/50 rounded-lg p-4 mb-2">
            🚧 {config.type} visualization requires additional React wrappers and is currently being rendered via native plugins.
          </div>
        </div>
      )}
    </div>
  );
};

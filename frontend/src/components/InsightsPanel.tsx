import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { insightsApi } from '../api/insights';
import type { InsightSeverity } from '../api/insights';
import { Loader2, AlertTriangle, AlertOctagon, CheckCircle, Info, Sparkles } from 'lucide-react';

interface InsightsPanelProps {
  datasetId: string;
}

const SeverityIcon = ({ severity }: { severity: InsightSeverity }) => {
  switch (severity) {
    case 'critical':
      return <AlertOctagon className="w-5 h-5 text-red-400" />;
    case 'warning':
      return <AlertTriangle className="w-5 h-5 text-amber-400" />;
    case 'success':
      return <CheckCircle className="w-5 h-5 text-emerald-400" />;
    case 'info':
    default:
      return <Info className="w-5 h-5 text-blue-400" />;
  }
};

const SeverityBorder = ({ severity }: { severity: InsightSeverity }) => {
  switch (severity) {
    case 'critical':
      return 'border-red-500/30 bg-red-500/10';
    case 'warning':
      return 'border-amber-500/30 bg-amber-500/10';
    case 'success':
      return 'border-emerald-500/30 bg-emerald-500/10';
    case 'info':
    default:
      return 'border-blue-500/30 bg-blue-500/10';
  }
};

export const InsightsPanel: React.FC<InsightsPanelProps> = ({ datasetId }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['insights', datasetId],
    queryFn: () => insightsApi.generate(datasetId),
    enabled: !!datasetId,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-10 h-10 text-brand-500 animate-spin mb-4" />
        <h3 className="text-lg font-medium text-white">Generating AI Insights...</h3>
        <p className="text-gray-400 mt-2 text-sm">Analyzing distributions and correlations</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 min-h-[400px] flex items-center justify-center">
        Failed to generate insights. The backend might not support this dataset size yet.
      </div>
    );
  }

  const insights = data?.insights || [];

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-xl p-6 shadow-lg min-h-[650px] animate-in fade-in zoom-in-95 duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-brand-400" />
        </div>
        <div>
          <h3 className="text-xl font-bold text-white">AI Insights</h3>
          <p className="text-sm text-gray-400">Auto-generated observations based on statistical profiling</p>
        </div>
      </div>

      {insights.length === 0 ? (
        <div className="flex items-center justify-center h-[400px] text-gray-500">
          No significant insights could be generated for this dataset.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {insights.map((insight, idx) => (
            <div 
              key={idx} 
              className={`p-5 rounded-xl border ${SeverityBorder({ severity: insight.severity })} flex flex-col gap-3 transition-colors hover:bg-opacity-80`}
            >
              <div className="flex items-start gap-3">
                <SeverityIcon severity={insight.severity} />
                <div>
                  <h4 className="font-semibold text-gray-100">{insight.title}</h4>
                  <span className="text-[10px] uppercase tracking-wider text-gray-400 font-medium">
                    {insight.insight_type.replace('_', ' ')}
                  </span>
                </div>
              </div>
              
              <p className="text-sm text-gray-300 leading-relaxed pl-8">
                {insight.description}
              </p>

              {insight.related_columns && insight.related_columns.length > 0 && (
                <div className="mt-auto pl-8 flex flex-wrap gap-1.5 pt-2">
                  {insight.related_columns.map(col => (
                    <span key={col} className="px-2 py-0.5 rounded text-[11px] bg-dark-900 border border-dark-600 text-gray-400">
                      {col}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

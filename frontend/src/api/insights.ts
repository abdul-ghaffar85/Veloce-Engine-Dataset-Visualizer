import { apiClient } from './client';

export type InsightType = 'trend' | 'correlation' | 'data_quality' | 'distribution' | 'semantic';
export type InsightSeverity = 'info' | 'warning' | 'critical' | 'success';

export interface Insight {
  insight_type: InsightType;
  severity: InsightSeverity;
  title: string;
  description: string;
  related_columns: string[];
}

export interface InsightsResponse {
  status: string;
  dataset_id: string;
  insights: Insight[];
}

export const insightsApi = {
  /**
   * Auto-generate AI insights for a dataset
   */
  generate: async (datasetId: string): Promise<InsightsResponse> => {
    const response = await apiClient.get<InsightsResponse>(`/insights/${datasetId}`);
    return response.data;
  },
};

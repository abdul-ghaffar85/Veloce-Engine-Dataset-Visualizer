import { apiClient } from './client';

export interface FilterCondition {
  column: string;
  operator: string;
  value?: any;
}

export interface AggregateMetric {
  column: string;
  function: string;
  alias?: string;
}

export interface SortCondition {
  column: string;
  order: 'asc' | 'desc';
}

export interface QueryRequest {
  filters?: FilterCondition[];
  group_by?: string[];
  aggregates?: AggregateMetric[];
  sort?: SortCondition[];
  limit?: number;
  offset?: number;
  chartType?: string;
  xAxis?: string | null;
  yAxis?: string | null;
  aggregation?: string;
}

export interface QueryResponse {
  status: string;
  dataset_id: string;
  total_rows: number;
  returned_rows: number;
  data: any[];
  execution_time_ms: number;
}

export const aggregationsApi = {
  /**
   * Execute a dynamic query for chart rendering
   */
  executeQuery: async (datasetId: string, query: QueryRequest): Promise<QueryResponse> => {
    const response = await apiClient.post<QueryResponse>(`/aggregations/${datasetId}`, query);
    return response.data;
  }
};

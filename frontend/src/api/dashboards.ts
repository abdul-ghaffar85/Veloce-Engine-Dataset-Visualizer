import { apiClient } from './client';

export interface DashboardResponse {
  dashboard: any; // Declarative dashboard layout from backend
}

export const dashboardsApi = {
  /**
   * Auto-generate a dashboard layout for the given dataset
   */
  generate: async (datasetId: string): Promise<DashboardResponse> => {
    const response = await apiClient.get<DashboardResponse>(`/dashboards/${datasetId}/generate`);
    return response.data;
  },
};

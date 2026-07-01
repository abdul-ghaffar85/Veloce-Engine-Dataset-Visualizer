import { apiClient } from './client';

export interface DatasetMetadata {
  dataset_id: string;
  original_filename: string;
  file_type: string;
  size_bytes: number;
  size_display: string;
  encoding: string;
  row_count: number;
  column_count: number;
  columns: any[];
  has_formula_warnings: boolean;
  formula_warning_count: number;
  uploaded_at: string;
}

export interface UploadResponse {
  message?: string;
  dataset: DatasetMetadata;
}

export interface ProfileResponse {
  profile: any; // Full profile schema from backend
}

export interface PreviewResponse {
  dataset_id: string;
  columns: string[];
  data: any[];
  total_rows: number;
  preview_rows: number;
}

export interface FieldStatistics {
  min: number | null;
  max: number | null;
  mean: number | null;
  median: number | null;
  sum: number | null;
  std: number | null;
  mode: string | null;
  top_values: { value: any, count: number, percentage: number }[];
  missing_count: number;
  missing_percentage: number;
  completeness: number;
  outlier_count: number;
  outlier_percentage: number;
}

export interface FieldDescriptor {
  field: string;
  position: number;
  semanticType: 'dimension' | 'metric' | 'time' | 'identifier' | 'text';
  dataType: 'string' | 'integer' | 'float' | 'boolean' | 'datetime';
  businessEntity: string | null;
  nullable: boolean;
  cardinality: number;
  uniquenessRatio: number;
  isUnique: boolean;
  isConstant: boolean;
  aggregations: string[];
  defaultAggregation: string | null;
  sampleValues: any[];
  uniqueValues: any[] | null;
  dateHierarchy: string[] | null;
  numericPrecision: number | null;
  statistics: FieldStatistics;
}

export interface DatasetFieldSchema {
  dataset_id: string;
  filename: string;
  row_count: number;
  column_count: number;
  fields: FieldDescriptor[];
  dimension_count: number;
  metric_count: number;
  time_count: number;
}

export interface FieldSchemaResponse {
  status: string;
  schema: DatasetFieldSchema;
}

export const datasetsApi = {
  /**
   * Upload a new dataset (CSV or Excel)
   */
  upload: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post<UploadResponse>('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Fetch metadata for a specific dataset
   */
  getMetadata: async (datasetId: string): Promise<UploadResponse> => {
    const response = await apiClient.get<UploadResponse>(`/datasets/${datasetId}`);
    return response.data;
  },

  /**
   * Get dataset profile summary
   */
  getProfile: async (datasetId: string): Promise<ProfileResponse> => {
    const response = await apiClient.get<ProfileResponse>(`/datasets/${datasetId}/profile`);
    return response.data;
  },
  
  /**
   * Get a preview of the dataset rows
   */
  getPreview: async (datasetId: string, rows: number = 50): Promise<PreviewResponse> => {
    const response = await apiClient.get<PreviewResponse>(`/datasets/${datasetId}/preview`, {
      params: { rows }
    });
    return response.data;
  },

  /**
   * Get the semantic field schema
   */
  getSchema: async (datasetId: string): Promise<FieldSchemaResponse> => {
    const response = await apiClient.get<FieldSchemaResponse>(`/datasets/${datasetId}/schema`);
    return response.data;
  }
};

import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { useQuery } from '@tanstack/react-query';
import { datasetsApi } from '../api/datasets';
import { Loader2 } from 'lucide-react';

interface PreviewTableProps {
  datasetId: string;
}

export const PreviewTable: React.FC<PreviewTableProps> = ({ datasetId }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['preview', datasetId],
    queryFn: () => datasetsApi.getPreview(datasetId, 50),
    enabled: !!datasetId,
  });

  const columnDefs = useMemo(() => {
    if (!data?.columns) return [];
    return data.columns.map(col => ({
      field: col,
      headerName: col,
      sortable: true,
      filter: true,
      resizable: true,
    }));
  }, [data?.columns]);

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-red-400">
        Failed to load dataset preview
      </div>
    );
  }

  return (
    <div className="h-full w-full ag-theme-alpine-dark">
      <AgGridReact
        rowData={data?.data || []}
        columnDefs={columnDefs}
        animateRows={true}
        rowSelection="multiple"
        defaultColDef={{
          flex: 1,
          minWidth: 150,
          filter: true,
          sortable: true,
          resizable: true,
        }}
      />
    </div>
  );
};

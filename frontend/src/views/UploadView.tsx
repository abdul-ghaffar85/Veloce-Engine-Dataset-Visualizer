import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileSpreadsheet, Loader2, AlertCircle } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { datasetsApi } from '../api/datasets';
import { useDatasetStore } from '../store/useDatasetStore';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export const UploadView: React.FC = () => {
  const navigate = useNavigate();
  const { setActiveDatasetId, setDatasetMetadata } = useDatasetStore();
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: datasetsApi.upload,
    onSuccess: (data) => {
      setActiveDatasetId(data.dataset.dataset_id);
      setDatasetMetadata(data.dataset);
      navigate(`/dataset/${data.dataset.dataset_id}/charts`);
    },
    onError: (error: any) => {
      const msg = error.response?.data?.detail || error.message || 'Failed to upload dataset';
      setUploadError(msg);
    }
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadError(null);
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    uploadMutation.mutate(file);
  }, [uploadMutation]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1,
    multiple: false
  });

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh]">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold tracking-tight text-white mb-3">
            Unlock AI-Powered Insights
          </h2>
          <p className="text-gray-400">
            Upload your CSV or Excel dataset. Our engines will instantly profile the data, detect relationships, and generate a tailored analytics dashboard.
          </p>
        </div>

        <div
          {...getRootProps()}
          className={twMerge(
            clsx(
              "group relative overflow-hidden rounded-2xl border-2 border-dashed transition-all duration-300 ease-in-out cursor-pointer",
              "bg-dark-800/50 backdrop-blur-sm",
              isDragActive ? "border-brand-500 bg-brand-500/5" : "border-dark-700 hover:border-brand-400 hover:bg-dark-700/50",
              isDragReject ? "border-red-500 bg-red-500/5" : "",
              uploadMutation.isPending ? "opacity-75 pointer-events-none" : ""
            )
          )}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center justify-center p-16 text-center">
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="w-16 h-16 text-brand-500 animate-spin mb-6" />
                <h3 className="text-xl font-semibold text-white mb-2">Analyzing Dataset...</h3>
                <p className="text-sm text-gray-400">Validating structure and extracting metadata</p>
              </>
            ) : (
              <>
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-brand-500/20 blur-xl rounded-full" />
                  <UploadCloud className={clsx(
                    "w-16 h-16 relative transition-colors duration-300",
                    isDragActive ? "text-brand-400" : "text-gray-400 group-hover:text-brand-400"
                  )} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  {isDragActive ? "Drop to upload" : "Drag & drop your dataset here"}
                </h3>
                <p className="text-sm text-gray-400 mb-6">
                  Supports .csv, .xlsx, .xls up to 100MB
                </p>
                <div className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-full bg-dark-700 text-gray-300">
                  <FileSpreadsheet className="w-4 h-4" />
                  Or click to browse files
                </div>
              </>
            )}
          </div>
        </div>

        {uploadError && (
          <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-red-200">Upload Failed</h4>
              <p className="text-sm text-red-300/80 mt-1">{uploadError}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

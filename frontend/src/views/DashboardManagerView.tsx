import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDashboardStore } from '../store/useDashboardStore';
import { LayoutDashboard, Plus, Copy, Trash2, ArrowRight } from 'lucide-react';

export const DashboardManagerView: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const { dashboards, createDashboard, deleteDashboard, duplicateDashboard, loadState } = useDashboardStore();

  useEffect(() => {
    loadState();
  }, [loadState]);

  // Filter dashboards for this dataset
  const datasetDashboards = Object.values(dashboards).filter(d => d.datasetId === datasetId);

  const handleCreate = () => {
    if (!datasetId) return;
    const name = `New Dashboard ${datasetDashboards.length + 1}`;
    const newDash = createDashboard(datasetId, name);
    navigate(`/dataset/${datasetId}/dashboards/${newDash.id}`);
  };

  return (
    <div className="p-8 max-w-6xl mx-auto h-full flex flex-col fade-in animate-in duration-500">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dashboards</h1>
          <p className="text-gray-400">Manage analytics dashboards for this dataset.</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => navigate(`/dataset/${datasetId}/charts`)}
            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg font-medium transition-colors border border-dark-600"
          >
            Chart Builder
          </button>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg font-medium transition-colors shadow-glow-brand"
          >
            <Plus className="w-5 h-5" />
            New Dashboard
          </button>
        </div>
      </div>

      {datasetDashboards.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 bg-dark-800/30 border border-dark-700 border-dashed rounded-2xl">
          <LayoutDashboard className="w-16 h-16 text-gray-600 mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No Dashboards Yet</h3>
          <p className="text-gray-400 mb-6 text-center max-w-md">
            Create a new dashboard to arrange your charts, build KPIs, and design interactive analytics views.
          </p>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-medium transition-colors shadow-lg"
          >
            <Plus className="w-5 h-5" />
            Create First Dashboard
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasetDashboards.map(dash => (
            <div 
              key={dash.id}
              className="bg-dark-800 border border-dark-700 rounded-xl p-6 hover:border-brand-500/50 hover:shadow-glow-brand transition-all group flex flex-col"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="bg-brand-500/20 p-3 rounded-lg">
                  <LayoutDashboard className="w-6 h-6 text-brand-400" />
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => duplicateDashboard(dash.id)}
                    className="p-1.5 text-gray-400 hover:text-white bg-dark-700 hover:bg-dark-600 rounded"
                    title="Duplicate"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button 
                    onClick={() => deleteDashboard(dash.id)}
                    className="p-1.5 text-gray-400 hover:text-red-400 bg-dark-700 hover:bg-dark-600 rounded"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <h3 className="text-lg font-semibold text-white mb-1 truncate">{dash.name}</h3>
              <p className="text-sm text-gray-400 mb-6">
                {dash.widgets.length} {dash.widgets.length === 1 ? 'Widget' : 'Widgets'}
              </p>
              
              <div className="mt-auto flex justify-between items-center">
                <span className="text-xs text-gray-500">
                  Updated {new Date(dash.updatedAt).toLocaleDateString()}
                </span>
                <button
                  onClick={() => navigate(`/dataset/${datasetId}/dashboards/${dash.id}`)}
                  className="flex items-center gap-1 text-sm font-medium text-brand-400 hover:text-brand-300"
                >
                  Open <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

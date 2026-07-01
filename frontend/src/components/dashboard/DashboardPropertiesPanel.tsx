import React from 'react';
import { useDashboardStore } from '../../store/useDashboardStore';
import { Settings, Hash, Shield, Droplet } from 'lucide-react';

export const DashboardPropertiesPanel: React.FC = () => {
  const { dashboards, activeDashboardId, activeWidgetId, updateDashboard, updateWidget } = useDashboardStore();

  if (!activeDashboardId) return null;
  const dashboard = dashboards[activeDashboardId];
  if (!dashboard) return null;

  const activeWidget = activeWidgetId ? dashboard.widgets.find(w => w.id === activeWidgetId) : null;

  return (
    <div className="w-80 bg-dark-800 border-l border-dark-700 h-full flex flex-col shrink-0">
      <div className="h-14 border-b border-dark-700 flex items-center px-4 shrink-0 bg-dark-900/50">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-brand-400" />
          {activeWidget ? 'Widget Properties' : 'Dashboard Properties'}
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
        {activeWidget ? (
          <>
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Styling</h3>
              
              <div>
                <label className="block text-xs text-gray-400 mb-1">Background Color</label>
                <div className="flex items-center bg-dark-900 border border-dark-700 rounded-lg p-1">
                  <Droplet className="w-4 h-4 text-gray-500 ml-2 shrink-0" />
                  <input 
                    type="text" 
                    value={activeWidget.style?.background || ''}
                    onChange={(e) => updateWidget(activeWidget.id, { style: { ...activeWidget.style, background: e.target.value } })}
                    placeholder="#1f2937 or transparent"
                    className="w-full bg-transparent border-none text-sm text-white focus:ring-0 focus:outline-none px-2"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Border Radius</label>
                <input 
                  type="text" 
                  value={activeWidget.style?.borderRadius || ''}
                  onChange={(e) => updateWidget(activeWidget.id, { style: { ...activeWidget.style, borderRadius: e.target.value } })}
                  placeholder="e.g. 12px or 1rem"
                  className="w-full bg-dark-900 border border-dark-700 text-sm text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-lg p-2"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Opacity (%)</label>
                <input 
                  type="number" 
                  min="0" max="100"
                  value={activeWidget.style?.opacity !== undefined ? activeWidget.style.opacity * 100 : 100}
                  onChange={(e) => {
                    const val = Math.max(0, Math.min(100, Number(e.target.value)));
                    updateWidget(activeWidget.id, { style: { ...activeWidget.style, opacity: val / 100 } });
                  }}
                  className="w-full bg-dark-900 border border-dark-700 text-sm text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-lg p-2"
                />
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t border-dark-700">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Metadata</h3>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Description</label>
                <textarea 
                  value={activeWidget.description || ''}
                  onChange={(e) => updateWidget(activeWidget.id, { description: e.target.value })}
                  rows={3}
                  placeholder="What does this widget show?"
                  className="w-full bg-dark-900 border border-dark-700 text-sm text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-lg p-2 resize-none custom-scrollbar"
                />
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">General</h3>
              
              <div>
                <label className="block text-xs text-gray-400 mb-1">Description</label>
                <textarea 
                  value={dashboard.description || ''}
                  onChange={(e) => updateDashboard(dashboard.id, { description: e.target.value })}
                  rows={4}
                  placeholder="Enter dashboard description..."
                  className="w-full bg-dark-900 border border-dark-700 text-sm text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-lg p-2 resize-none custom-scrollbar"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1 flex items-center gap-2">
                  <Shield className="w-3 h-3" /> Owner
                </label>
                <input 
                  type="text" 
                  value={dashboard.owner || ''}
                  onChange={(e) => updateDashboard(dashboard.id, { owner: e.target.value })}
                  placeholder="e.g. Sales Team"
                  className="w-full bg-dark-900 border border-dark-700 text-sm text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-lg p-2"
                />
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1 flex items-center gap-2">
                  <Hash className="w-3 h-3" /> Tags (comma separated)
                </label>
                <input 
                  type="text" 
                  value={dashboard.tags?.join(', ') || ''}
                  onChange={(e) => {
                    const tags = e.target.value.split(',').map(t => t.trim()).filter(Boolean);
                    updateDashboard(dashboard.id, { tags });
                  }}
                  placeholder="e.g. Q3, Finance"
                  className="w-full bg-dark-900 border border-dark-700 text-sm text-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 rounded-lg p-2"
                />
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t border-dark-700">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Appearance</h3>
              <div>
                <label className="block text-xs text-gray-400 mb-2">Theme Engine</label>
                <div className="grid grid-cols-2 gap-2">
                  <button 
                    onClick={() => updateDashboard(dashboard.id, { theme: 'dark' })}
                    className={`p-2 rounded-lg border text-sm font-medium transition-colors ${dashboard.theme === 'dark' ? 'bg-brand-500/20 border-brand-500 text-brand-400' : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-dark-500 hover:text-white'}`}
                  >
                    Dark
                  </button>
                  <button 
                    onClick={() => updateDashboard(dashboard.id, { theme: 'light' })}
                    className={`p-2 rounded-lg border text-sm font-medium transition-colors ${dashboard.theme === 'light' ? 'bg-brand-500/20 border-brand-500 text-brand-400' : 'bg-dark-900 border-dark-700 text-gray-400 hover:border-dark-500 hover:text-white'}`}
                  >
                    Light
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

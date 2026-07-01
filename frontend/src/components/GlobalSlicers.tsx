import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { useDatasetStore } from '../store/useDatasetStore';
import { Filter as FilterIcon, X } from 'lucide-react';

export const GlobalSlicers: React.FC = () => {
  const { globalFilters, updateGlobalFilter, removeGlobalFilter } = useDatasetStore();
  const { setNodeRef, isOver } = useDroppable({
    id: 'globalSlicers',
  });

  return (
    <div 
      ref={setNodeRef}
      className={`min-h-[64px] flex-shrink-0 border-b border-dark-700 bg-dark-800 p-3 flex flex-wrap gap-3 items-center transition-colors ${
        isOver ? 'bg-brand-500/10 border-brand-500/50' : ''
      }`}
    >
      <div className="flex items-center gap-2 text-gray-400 mr-4">
        <FilterIcon className="w-4 h-4" />
        <span className="text-xs font-semibold uppercase tracking-wider">Global Slicers</span>
      </div>

      {globalFilters.length === 0 ? (
        <div className="text-sm text-gray-500 italic opacity-70">
          Drag dimensions here to add global filters...
        </div>
      ) : (
        globalFilters.map(filter => (
          <div key={filter.id} className="bg-dark-900 border border-dark-600 rounded-lg px-3 py-2 flex items-center gap-3 min-w-[200px]">
            <div className="flex flex-col flex-1">
              <span className="text-xs font-medium text-gray-400 mb-1">{filter.field.field}</span>
              {filter.field.uniqueValues && filter.field.uniqueValues.length > 0 ? (
                <select
                  value={filter.value}
                  onChange={(e) => updateGlobalFilter(filter.id, { value: e.target.value })}
                  className="bg-dark-800 text-sm text-white border border-dark-600 rounded outline-none focus:border-brand-500 p-1 w-full"
                >
                  <option value="">(All)</option>
                  {filter.field.uniqueValues.slice(0, 100).map(val => (
                    <option key={val} value={val}>{val}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  placeholder="Type to filter..."
                  value={filter.value}
                  onChange={(e) => updateGlobalFilter(filter.id, { value: e.target.value })}
                  className="bg-dark-800 text-sm text-white border border-dark-600 rounded outline-none focus:border-brand-500 p-1 w-full placeholder-gray-600"
                />
              )}
            </div>
            <button 
              onClick={() => removeGlobalFilter(filter.id)}
              className="text-gray-500 hover:text-red-400 hover:bg-dark-800 p-1 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))
      )}
    </div>
  );
};

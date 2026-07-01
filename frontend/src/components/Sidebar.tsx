import React, { useState } from 'react';
import { useDatasetStore } from '../store/useDatasetStore';
import { 
  Hash, 
  Type, 
  Calendar, 
  ToggleLeft, 
  Search,
  ChevronDown,
  Info,
  GripVertical,
  Plus
} from 'lucide-react';
import type { FieldDescriptor } from '../api/datasets';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { motion, AnimatePresence } from 'framer-motion';
import { CalculatedFieldModal } from './CalculatedFieldModal';

const DataTypeIcon: React.FC<{ type: string; className?: string }> = ({ type, className = "w-4 h-4" }) => {
  switch (type) {
    case 'integer':
    case 'float':
      return <Hash className={`${className} text-blue-400`} />;
    case 'datetime':
      return <Calendar className={`${className} text-orange-400`} />;
    case 'boolean':
      return <ToggleLeft className={`${className} text-purple-400`} />;
    case 'string':
    default:
      return <Type className={`${className} text-green-400`} />;
  }
};

const FieldItem: React.FC<{ field: FieldDescriptor }> = ({ field }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `field-${field.field}`,
    data: { field }
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 100 : 'auto',
  };

  return (
    <div 
      ref={setNodeRef}
      style={style}
      className={`group flex items-center justify-between px-2 py-2 text-sm text-gray-300 hover:bg-dark-700 hover:text-white rounded-md transition-colors border ${isDragging ? 'border-brand-500 bg-dark-700' : 'border-transparent hover:border-dark-600'}`}
    >
      <div className="flex items-center gap-2 overflow-hidden flex-1">
        <div 
          {...listeners} 
          {...attributes}
          className="cursor-grab active:cursor-grabbing p-1 -ml-1 text-gray-500 hover:text-gray-300 rounded"
        >
          <GripVertical className="w-4 h-4" />
        </div>
        <DataTypeIcon type={field.dataType} />
        <span className="truncate select-none font-medium">{field.field}</span>
      </div>
      
      {/* Tooltip trigger / Info icon on hover */}
      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center">
        <div className="relative group/tooltip">
          <Info className="w-4 h-4 text-gray-500 hover:text-gray-300" />
          
          {/* Tooltip Content */}
          <div className="absolute left-full top-0 ml-2 w-64 p-3 bg-dark-800/95 backdrop-blur-xl border border-dark-600 rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.5)] opacity-0 group-hover/tooltip:opacity-100 pointer-events-none transition-opacity z-50">
            <h4 className="font-semibold text-white mb-2">{field.field}</h4>
            <div className="space-y-1 text-xs text-gray-400">
              <div className="flex justify-between">
                <span>Data Type:</span>
                <span className="text-gray-200 capitalize">{field.dataType}</span>
              </div>
              <div className="flex justify-between">
                <span>Semantic Type:</span>
                <span className="text-gray-200 capitalize">{field.semanticType}</span>
              </div>
              {field.businessEntity && (
                <div className="flex justify-between">
                  <span>Entity:</span>
                  <span className="text-gray-200 capitalize">{field.businessEntity}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>Unique Values:</span>
                <span className="text-gray-200">{field.cardinality?.toLocaleString() || 'N/A'}</span>
              </div>
              
              {field.sampleValues && field.sampleValues.length > 0 && (
                <div className="mt-2 pt-2 border-t border-dark-700">
                  <span className="block mb-1">Sample Values:</span>
                  <div className="flex flex-wrap gap-1">
                    {field.sampleValues.slice(0, 3).map((v, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-dark-900 rounded border border-dark-700 text-gray-300 truncate max-w-[80px]">
                        {v?.toString() || 'null'}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const FolderGroup: React.FC<{
  title: string;
  fields: FieldDescriptor[];
  defaultOpen?: boolean;
}> = ({ title, fields, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (fields.length === 0) return null;

  return (
    <div className="mb-4">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 w-full text-left px-2 mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-300 transition-colors"
      >
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? '' : '-rotate-90'}`} />
        {title}
        <span className="ml-auto bg-dark-700 px-1.5 py-0.5 rounded text-[10px] font-medium text-gray-400">
          {fields.length}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="space-y-0.5 pt-1">
              {fields.map(field => (
                <FieldItem key={field.field} field={field} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const Sidebar: React.FC = () => {
  const { fieldSchema, calculatedFields } = useDatasetStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState<'original' | 'az'>('original');
  const [typeFilter, setTypeFilter] = useState<'all' | 'string' | 'numeric' | 'date'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (!fieldSchema) return null;

  let allFields = [...fieldSchema.fields, ...calculatedFields];

  // Filtering
  if (searchTerm) {
    allFields = allFields.filter(f => f.field.toLowerCase().includes(searchTerm.toLowerCase()));
  }
  if (typeFilter === 'string') {
    allFields = allFields.filter(f => f.dataType === 'string');
  } else if (typeFilter === 'numeric') {
    allFields = allFields.filter(f => ['integer', 'float'].includes(f.dataType));
  } else if (typeFilter === 'date') {
    allFields = allFields.filter(f => f.dataType === 'datetime');
  }

  // Sorting
  if (sortOrder === 'az') {
    allFields.sort((a, b) => a.field.localeCompare(b.field));
  }

  // Grouping
  const groups: Record<string, FieldDescriptor[]> = {
    'Calculated Fields': [],
    'Dates & Time': [],
    'Geospatial': [],
    'Identifiers': [],
    'Dimensions': [],
    'Metrics': [],
  };

  allFields.forEach(f => {
    // Determine which group this field belongs to
    if (calculatedFields.find(cf => cf.field === f.field)) {
      groups['Calculated Fields'].push(f);
    } else if (f.semanticType === 'metric') {
      groups['Metrics'].push(f);
    } else if (f.semanticType === 'time' || f.dataType === 'datetime') {
      groups['Dates & Time'].push(f);
    } else if (f.businessEntity === 'location') {
      groups['Geospatial'].push(f);
    } else if (f.semanticType === 'identifier') {
      groups['Identifiers'].push(f);
    } else {
      groups['Dimensions'].push(f);
    }
  });

  return (
    <>
      <div className="w-80 flex-shrink-0 bg-dark-800/60 backdrop-blur-md border-r border-dark-700/50 h-[calc(100vh-64px)] flex flex-col overflow-hidden sticky top-16">
        
        {/* Sidebar Header & Controls */}
        <div className="p-4 border-b border-dark-700 space-y-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="w-full py-1.5 px-3 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 shadow-sm"
          >
            <Plus className="w-4 h-4" /> Create Calculated Field
          </button>
          
          <div className="relative">
            <Search className="w-4 h-4 text-gray-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search fields..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg pl-9 pr-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all"
            />
          </div>

          <div className="flex gap-2">
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'original' | 'az')}
              className="flex-1 bg-dark-900 border border-dark-600 text-xs text-gray-300 rounded px-2 py-1.5 outline-none cursor-pointer hover:border-dark-500 transition-colors"
            >
              <option value="original">Original Order</option>
              <option value="az">A-Z</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as any)}
              className="flex-1 bg-dark-900 border border-dark-600 text-xs text-gray-300 rounded px-2 py-1.5 outline-none cursor-pointer hover:border-dark-500 transition-colors"
            >
              <option value="all">All Types</option>
              <option value="string">Text</option>
              <option value="numeric">Numbers</option>
              <option value="date">Dates</option>
            </select>
          </div>
        </div>

        {/* Fields List */}
        <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
          {allFields.length === 0 ? (
            <div className="px-3 py-4 text-sm text-gray-500 italic text-center">
              No fields match your filters.
            </div>
          ) : (
            <>
              <FolderGroup title="Calculated Fields" fields={groups['Calculated Fields']} />
              <FolderGroup title="Dates & Time" fields={groups['Dates & Time']} />
              <FolderGroup title="Geospatial" fields={groups['Geospatial']} />
              <FolderGroup title="Identifiers" fields={groups['Identifiers']} defaultOpen={false} />
              <FolderGroup title="Dimensions" fields={groups['Dimensions']} />
              <FolderGroup title="Metrics" fields={groups['Metrics']} />
            </>
          )}
        </div>
      </div>

      <CalculatedFieldModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
      />
    </>
  );
};

import React, { useState } from 'react';
import { useDatasetStore } from '../store/useDatasetStore';
import { X, Plus, Type, Hash } from 'lucide-react';
import type { FieldDescriptor } from '../api/datasets';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const CalculatedFieldModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { addCalculatedField } = useDatasetStore();
  const [fieldName, setFieldName] = useState('');
  const [formula, setFormula] = useState('');
  const [dataType, setDataType] = useState<'string' | 'float'>('float');
  const [semanticType, setSemanticType] = useState<'metric' | 'dimension'>('metric');

  if (!isOpen) return null;

  const handleSave = () => {
    if (!fieldName.trim() || !formula.trim()) return;

    const newField: FieldDescriptor = {
      field: fieldName,
      dataType: dataType,
      semanticType: semanticType as 'metric' | 'dimension',
      cardinality: 0,
      sampleValues: [],
      defaultAggregation: semanticType === 'metric' ? 'sum' : null,
      position: 999, // default last
      businessEntity: null,
      nullable: true,
      uniquenessRatio: 0,
      isUnique: false,
      isConstant: false,
      aggregations: semanticType === 'metric' ? ['sum', 'mean', 'min', 'max'] : [],
      uniqueValues: null,
      dateHierarchy: null,
      numericPrecision: dataType === 'float' ? 2 : null,
      statistics: {
        min: null, max: null, mean: null, median: null, sum: null, std: null, mode: null,
        top_values: [], missing_count: 0, missing_percentage: 0, completeness: 100, outlier_count: 0, outlier_percentage: 0
      }
    };

    addCalculatedField(newField);
    onClose();
    setFieldName('');
    setFormula('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-dark-800 border border-dark-600 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Plus className="w-5 h-5 text-brand-400" />
            Create Calculated Field
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Field Name</label>
            <input
              type="text"
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              placeholder="e.g. Profit Margin"
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Data Type</label>
              <div className="flex bg-dark-900 border border-dark-600 rounded-lg p-1">
                <button
                  onClick={() => setDataType('float')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    dataType === 'float' ? 'bg-dark-700 text-brand-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  <Hash className="w-4 h-4" /> Number
                </button>
                <button
                  onClick={() => setDataType('string')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    dataType === 'string' ? 'bg-dark-700 text-brand-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  <Type className="w-4 h-4" /> Text
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Role</label>
              <div className="flex bg-dark-900 border border-dark-600 rounded-lg p-1">
                <button
                  onClick={() => setSemanticType('metric')}
                  className={`flex-1 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    semanticType === 'metric' ? 'bg-dark-700 text-brand-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Metric
                </button>
                <button
                  onClick={() => setSemanticType('dimension')}
                  className={`flex-1 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    semanticType === 'dimension' ? 'bg-dark-700 text-brand-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Dimension
                </button>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5 flex justify-between">
              Formula
              <span className="text-xs text-brand-400 bg-brand-400/10 px-1.5 py-0.5 rounded">Pandas Syntax Eval</span>
            </label>
            <textarea
              value={formula}
              onChange={(e) => setFormula(e.target.value)}
              placeholder="e.g. (Profit / Sales) * 100"
              rows={3}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all font-mono text-sm resize-none"
            />
            <p className="mt-1.5 text-xs text-gray-500">
              Note: Full expression evaluation requires backend parsing. This is a UI prototype for Phase 6.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-dark-700 bg-dark-800 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            disabled={!fieldName.trim() || !formula.trim()}
            className="px-4 py-2 text-sm font-medium bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save Field
          </button>
        </div>

      </div>
    </div>
  );
};

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import clsx from 'clsx';

interface KPICardProps {
  card: {
    title: string;
    value: string | number;
    trend?: 'up' | 'down' | 'neutral';
    trend_value?: string;
  };
}

export const KPICard: React.FC<KPICardProps> = ({ card }) => {
  return (
    <div className="bg-dark-800 border border-dark-700 rounded-xl p-5 shadow-lg flex flex-col justify-between transition-all hover:border-brand-500/50 hover:bg-dark-700/50">
      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider">{card.title}</h4>
      <div className="mt-4 flex items-end justify-between">
        <span className="text-3xl font-bold text-white tracking-tight">{card.value}</span>
        
        {card.trend && (
          <div className={clsx(
            "flex items-center gap-1 text-sm font-medium",
            card.trend === 'up' ? "text-green-400" :
            card.trend === 'down' ? "text-red-400" : "text-gray-400"
          )}>
            {card.trend === 'up' && <TrendingUp className="w-4 h-4" />}
            {card.trend === 'down' && <TrendingDown className="w-4 h-4" />}
            {card.trend === 'neutral' && <Minus className="w-4 h-4" />}
            {card.trend_value}
          </div>
        )}
      </div>
    </div>
  );
};

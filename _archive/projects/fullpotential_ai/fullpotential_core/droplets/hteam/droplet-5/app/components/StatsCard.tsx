'use client';

import { LucideIcon } from 'lucide-react';
import Card from '../shared/components/Card';
import LoadingSpinner from '../shared/components/LoadingSpinner';
import { CHANGE_TYPES } from '../shared/utils/constants';

interface StatsCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: keyof typeof CHANGE_TYPES;
  icon: LucideIcon;
  loading?: boolean;
}

export default function StatsCard({ 
  title, 
  value, 
  change, 
  changeType = 'neutral', 
  icon: Icon,
  loading = false 
}: StatsCardProps) {

  return (
    <Card hover className="group">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-slate-600 dark:text-slate-400 text-sm font-medium mb-1">{title}</p>
          {loading ? (
            <div className="flex items-center gap-2">
              <LoadingSpinner size="sm" />
              <div className="h-6 w-16 bg-slate-200 dark:bg-slate-700 rounded animate-pulse"></div>
            </div>
          ) : (
            <p className="text-3xl font-bold text-slate-900 dark:text-white mb-1">{value}</p>
          )}
          {change && !loading && (
            <p className={`text-sm ${CHANGE_TYPES[changeType]}`}>
              {change}
            </p>
          )}
        </div>
        <div className="ml-4">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl flex items-center justify-center group-hover:from-blue-600 group-hover:to-purple-600 transition-all shadow-md group-hover:shadow-lg">
            <Icon size={24} className="text-white" />
          </div>
        </div>
      </div>
    </Card>
  );
}
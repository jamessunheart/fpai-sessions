import { LucideIcon } from 'lucide-react';
import { Card } from '../../../shared/components';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
  loading?: boolean;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'blue',
  loading = false
}: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-500/20 dark:text-green-400',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-500/20 dark:text-yellow-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-500/20 dark:text-red-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400'
  };

  return (
    <Card className="relative overflow-hidden group" hover>
      {loading ? (
        <div className="animate-pulse">
          <div className="flex items-center justify-between mb-4">
            <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-20"></div>
            <div className="w-10 h-10 bg-gray-200 dark:bg-slate-700 rounded-lg"></div>
          </div>
          <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-16 mb-2"></div>
          <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-24"></div>
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</h3>
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]} group-hover:scale-110 transition-transform duration-200`}>
              <Icon size={20} />
            </div>
          </div>

          {/* Value */}
          <div className="mb-2">
            <span className="text-2xl font-bold text-black dark:text-white">{value}</span>
            {trend && (
              <span className={`ml-2 text-sm font-medium ${
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              }`}>
                {trend.isPositive ? '↗' : '↘'} {Math.abs(trend.value)}%
              </span>
            )}
          </div>

          {/* Subtitle */}
          {subtitle && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{subtitle}</p>
          )}

          {/* Decorative gradient */}
          <div className={`absolute -bottom-1 -right-1 w-20 h-20 rounded-full opacity-10 ${colorClasses[color]} group-hover:scale-150 transition-transform duration-500`}></div>
        </>
      )}
    </Card>
  );
}
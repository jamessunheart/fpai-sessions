'use client';

import { useState, useEffect } from 'react';
import { useApi } from '../../../shared/hooks/useApi';
import { api } from '../../../lib/api';
import { Card, LoadingSpinner } from '../../../shared/components';
import MetricCard from './MetricCard';
import ProgressRing from './ProgressRing';
import SprintChart from './SprintChart';
import AIChatPanel from './AIChatPanel';
import { 
  TrendingUp, 
  Server, 
  Zap, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Calendar,
  RefreshCw,
  Download
} from 'lucide-react';

interface DailyDigestData {
  status: number;
  message: string;
  data: {
    records: Array<{
      id: string;
      createdTime: string;
      fields: {
        Date: string;
        Total_Droplets: number;
        Active_Droplets: number;
        Uptime_Percentage: number;
        Total_Sprints: number;
        Completed_Sprints: number;
        Active_Sprints: number;
        Pending_Sprints: number;
        New_Sprints_Today: number;
        Total_Proofs: number;
        Verified_Proofs: number;
        Failed_Proofs: number;
        Average_CPU: number;
        Average_RAM: number;
        Daily_Summary: string;
      };
    }>;
  };
  summary: {
    date: string;
    total_droplets: number;
    active_droplets: number;
    uptime_percentage: string;
    new_sprints_today: number;
    total_sprints_in_system: number;
    completed_sprints: number;
    active_sprints: number;
    pending_sprints: number;
    proofs_submitted_today: number;
    proofs_verified_today: number;
  };
}

export default function AnalyticsDashboard() {
  const { data: digestData, loading: digestLoading, refetch: refetchDigest } = useApi<DailyDigestData>(() => api.getDailyDigest(), []);
  const { data: dashboardData, loading: dashboardLoading, refetch: refetchDashboard } = useApi(() => api.getDashboard(), []);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  
  const loading = digestLoading || dashboardLoading;

  useEffect(() => {
    if (digestData) {
      setLastUpdated(new Date());
    }
  }, [digestData]);

  const handleRefresh = () => {
    refetchDigest();
    refetchDashboard();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-48 mb-2"></div>
            <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-64"></div>
          </div>
          <div className="h-10 bg-gray-200 dark:bg-slate-700 rounded w-32"></div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <MetricCard
              key={i}
              title=""
              value=""
              icon={TrendingUp}
              loading={true}
            />
          ))}
        </div>
      </div>
    );
  }

  if (!digestData) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-black dark:text-white mb-2">
            No Analytics Data
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Unable to load analytics data. Please try again.
          </p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { summary, data } = digestData;
  
  // Use live droplet data from drop1, sprint data from drop2
  const liveDroplets = dashboardData?.droplets || [];
  const liveSummary = dashboardData?.summary || { total: 0, healthy: 0, down: 0 };
  
  // Calculate live CPU/RAM averages
  const avgCpu = liveDroplets.length > 0 ? liveDroplets.reduce((acc: number, d: any) => acc + d.cpu, 0) / liveDroplets.length : 0;
  const avgRam = liveDroplets.length > 0 ? liveDroplets.reduce((acc: number, d: any) => acc + d.mem, 0) / liveDroplets.length : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-black dark:text-white">Analytics Dashboard</h2>
          <p className="text-gray-600 dark:text-gray-400 flex items-center gap-2 mt-1">
            <Calendar size={16} />
            {summary.date} • Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
            <Download size={16} />
            Export
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="System Uptime"
          value={`${Math.round((liveSummary.healthy / liveSummary.total) * 100 || 0)}%`}
          subtitle="Infrastructure health"
          icon={Server}
          color="green"
        />
        <MetricCard
          title="New Sprints Today"
          value={summary.new_sprints_today}
          subtitle={`${summary.total_sprints_in_system} total in system`}
          icon={Zap}
          color="blue"
        />
        <MetricCard
          title="Completed Sprints"
          value={summary.completed_sprints}
          subtitle={`${Math.round((summary.completed_sprints / summary.total_sprints_in_system) * 100)}% completion rate`}
          icon={CheckCircle}
          color="green"
        />
        <MetricCard
          title="Active Droplets"
          value={`${liveSummary.healthy}/${liveSummary.total}`}
          subtitle="Infrastructure status"
          icon={Server}
          color={liveSummary.healthy === liveSummary.total ? 'green' : 'yellow'}
        />
      </div>

      {/* Charts and Visual Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sprint Distribution */}
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-black dark:text-white">Sprint Distribution</h3>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {summary.total_sprints_in_system} total sprints
            </div>
          </div>
          <SprintChart
            data={{
              completed: summary.completed_sprints,
              active: summary.active_sprints,
              pending: summary.pending_sprints
            }}
          />
        </Card>

        {/* System Health */}
        <Card className="flex flex-col items-center justify-center">
          <h3 className="text-lg font-semibold text-black dark:text-white mb-6">System Health</h3>
          <ProgressRing
            percentage={Math.round((liveSummary.healthy / liveSummary.total) * 100 || 0)}
            color="#10B981"
            size={140}
          />
          <div className="mt-4 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {liveSummary.healthy} of {liveSummary.total} droplets online
            </p>
          </div>
        </Card>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Proofs Submitted"
          value={summary.proofs_submitted_today}
          subtitle="Today's submissions"
          icon={CheckCircle}
          color="purple"
        />
        <MetricCard
          title="Proofs Verified"
          value={summary.proofs_verified_today}
          subtitle="Verification rate"
          icon={CheckCircle}
          color="green"
        />
        <MetricCard
          title="Average CPU"
          value={`${Math.round(avgCpu)}%`}
          subtitle="System performance"
          icon={TrendingUp}
          color={avgCpu > 80 ? 'red' : avgCpu > 60 ? 'yellow' : 'green'}
        />
        <MetricCard
          title="Average RAM"
          value={`${Math.round(avgRam)}%`}
          subtitle="Memory usage"
          icon={TrendingUp}
          color={avgRam > 80 ? 'red' : avgRam > 60 ? 'yellow' : 'green'}
        />
      </div>

      {/* Daily Summary */}
      <Card>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <TrendingUp className="text-blue-600 dark:text-blue-400" size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-black dark:text-white mb-2">System Summary</h3>
            <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
              Today: {summary.new_sprints_today} new sprints created, {summary.proofs_submitted_today} proofs submitted. 
              Infrastructure: {liveSummary.healthy}/{liveSummary.total} droplets online 
              ({Math.round((liveSummary.healthy / liveSummary.total) * 100 || 0)}% uptime). 
              Average system load: CPU {Math.round(avgCpu)}%, RAM {Math.round(avgRam)}%. 
              Sprint progress: {summary.completed_sprints} completed, {summary.active_sprints} active, {summary.pending_sprints} pending.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
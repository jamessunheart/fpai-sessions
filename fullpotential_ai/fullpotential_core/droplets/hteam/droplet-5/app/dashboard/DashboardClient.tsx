'use client';

import { useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import ModernSidebar from '../components/ModernSidebar';
import SprintTable from '../components/SprintTable';
import StatsGrid from '../features/dashboard/components/StatsGrid';
import DropletsView from '../features/dashboard/components/DropletsView';
import { useApi } from '../shared/hooks/useApi';
import { useAutoNotifications } from '../shared/hooks/useAutoNotifications';
import { api } from '../lib/api';
import { DashboardStats } from '../types';

export default function DashboardClient() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const view = searchParams.get('view') || 'overview';
  
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useAutoNotifications();
  const { data: sprintsData, loading: sprintsLoading } = useApi(() => api.getSprints(), []);
  const { data: dashboardData, loading: dashboardLoading } = useApi(() => api.getDashboard(), []);
  
  const loading = sprintsLoading || dashboardLoading;
  const sprints = sprintsData?.records || [];
  const droplets = dashboardData?.droplets || [];
  const summary = dashboardData?.summary || { total: 0, healthy: 0, down: 0, cost_hour_total: 0 };

  const stats: DashboardStats = useMemo(() => ({
    totalSprints: sprints.length,
    activeSprints: sprints.filter(s => s.fields.Status === 'Active').length,
    completedSprints: sprints.filter(s => s.fields.Status === 'Done').length,
    totalDroplets: summary.total,
    activeDroplets: summary.healthy,
    uptime: summary.total > 0 ? (summary.healthy / summary.total) * 100 : 0,
    avgCpu: droplets.length > 0 ? droplets.reduce((acc, d) => acc + d.cpu, 0) / droplets.length : 0,
    avgRam: droplets.length > 0 ? droplets.reduce((acc, d) => acc + d.mem, 0) / droplets.length : 0,
  }), [sprints, droplets, summary]);

  if (authLoading || !isAuthenticated) return null;

  const title = view === 'droplets' ? 'Droplets' : 'Overview';

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 dark:from-slate-950 dark:via-slate-900 dark:to-slate-900">
      <ModernSidebar />
      
      <main className="flex-1 overflow-auto">
        <div className="h-full flex flex-col p-6">
          <header className="backdrop-blur-md bg-white/90 dark:bg-slate-900/90 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-lg mb-6">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              {title}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">Real-time monitoring and management</p>
          </header>

          <div className="flex-1 overflow-auto">
            {view === 'overview' && (
              <div className="space-y-4">
                <StatsGrid stats={stats} loading={loading} />
                <SprintTable sprints={sprints.slice(0, 10)} loading={loading} />
              </div>
            )}
            
            {view === 'droplets' && <DropletsView />}
          </div>
        </div>
      </main>
    </div>
  );
}

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import ModernSidebar from '../components/ModernSidebar';
import AnalyticsDashboard from '../features/analytics/components/AnalyticsDashboard';

export default function AnalyticsPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading || !isAuthenticated) return null;

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <ModernSidebar />
      
      <main className="flex-1 overflow-auto">
        <div className="h-full flex flex-col p-6">
          <header className="backdrop-blur-sm bg-white/50 dark:bg-slate-900/50 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-lg mb-6">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Analytics
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400">Performance metrics and insights</p>
          </header>

          <div className="flex-1 overflow-auto">
            <AnalyticsDashboard />
          </div>
        </div>
      </main>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import ModernSidebar from '../components/ModernSidebar';
import AIChatPanel from '../features/analytics/components/AIChatPanel';
import { MessageCircle } from 'lucide-react';

export default function TeamSupportPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [systemData, setSystemData] = useState(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    fetchSystemData();
  }, []);

  const fetchSystemData = async () => {
    try {
      const res = await fetch('/api/analyze-system');
      const data = await res.json();
      setSystemData(data);
    } catch (error) {
      console.error('Failed to fetch system data:', error);
    }
  };

  if (loading || !isAuthenticated) return null;

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <ModernSidebar />
      
      <main className="flex-1 overflow-auto">
        <div className="h-full flex flex-col p-6">
          <header className="backdrop-blur-sm bg-white/50 dark:bg-slate-900/50 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-lg mb-6">
            <div className="flex items-center gap-3">
              <MessageCircle className="w-7 h-7 text-blue-600 dark:text-blue-400" />
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">Team Support</h1>
                <p className="text-sm text-slate-600 dark:text-slate-400">AI-powered assistant for system analysis and support</p>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-auto">
            <AIChatPanel systemData={systemData} />
          </div>
        </div>
      </main>
    </div>
  );
}

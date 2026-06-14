'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import ModernSidebar from '../components/ModernSidebar';
import DropletCard from '../features/infrastructure/components/DropletCard';
import DropletDetails from '../features/infrastructure/components/DropletDetails';
import { Card } from '../shared/components';
import { useApi } from '../shared/hooks/useApi';
import { api } from '../lib/api';
import { Droplet } from '../types';
import { Server, Activity, AlertCircle, Search, Filter, Info } from 'lucide-react';

export default function InfrastructurePage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [selectedDroplet, setSelectedDroplet] = useState<Droplet | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const { data: registryData, loading } = useApi(() => api.getRegistryDroplets(), []);
  const [healthData, setHealthData] = useState<Record<string, any>>({});
  const [healthLoading, setHealthLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [canRefresh, setCanRefresh] = useState(true);

  // Fetch health data for all droplets
  const fetchHealthData = async (isManual = false) => {
    if (!registryData?.droplets) return;
    if (isManual && !canRefresh) return;
    
    setHealthLoading(true);
    if (isManual) {
      setCanRefresh(false);
      setTimeout(() => setCanRefresh(true), 5000); // 5 second cooldown
    }
    
    const healthResults: Record<string, any> = {};
    
    await Promise.all(
      registryData.droplets.map(async (droplet: any) => {
        try {
          // For Droplet #5, use dashboard.fullpotential.ai instead of drop5.fullpotential.ai
          const host = droplet.id === 'drop5.fullpotential.ai' || droplet.id === '5' 
            ? 'dashboard.fullpotential.ai' 
            : droplet.host;
          const response = await fetch(`/api/health-check?host=${encodeURIComponent(host)}`);
          const data = await response.json();
          healthResults[droplet.id] = data;
        } catch (error) {
          healthResults[droplet.id] = { available: false };
        }
      })
    );
    
    setHealthData(healthResults);
    setHealthLoading(false);
    setLastRefresh(new Date());
  };

  useEffect(() => {
    fetchHealthData();
    // Auto-refresh disabled to prevent constant re-renders
    // Users can manually refresh using the button
  }, [registryData]);
  
  // Deduplicate droplets (without health data to prevent re-render)
  const allDroplets = useMemo(() => {
    const droplets = registryData?.droplets || [];
    const deduped = new Map();
    
    droplets.forEach((d: any) => {
      const existing = deduped.get(d.id);
      if (!existing) {
        deduped.set(d.id, d);
      } else {
        // Keep the one with more fields
        const existingFields = Object.keys(existing).filter(k => existing[k] != null).length;
        const newFields = Object.keys(d).filter(k => d[k] != null).length;
        if (newFields > existingFields) {
          deduped.set(d.id, d);
        }
      }
    });
    
    return Array.from(deduped.values());
  }, [registryData]);

  const filteredDroplets = useMemo(() => {
    return allDroplets.filter((d: any) => {
      const matchesSearch = !searchQuery || 
        d.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.host?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.role?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || d.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [allDroplets, searchQuery, statusFilter]);

  const stats = useMemo(() => {
    const active = allDroplets.filter((d: any) => healthData[d.id]?.status === 'active').length;
    const inactive = allDroplets.filter((d: any) => healthData[d.id]?.status === 'inactive').length;
    const error = allDroplets.filter((d: any) => healthData[d.id]?.status === 'error').length;
    const offline = allDroplets.filter((d: any) => !healthData[d.id]?.available).length;
    const rawTotal = registryData?.count || 0;
    
    return { total: allDroplets.length, active, inactive, error, offline, rawTotal };
  }, [allDroplets, healthData, registryData]);



  if (authLoading || !isAuthenticated) return null;

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <ModernSidebar />
      
      <main className="flex-1 overflow-auto">
        <div className="h-full flex flex-col p-6">
          <header className="backdrop-blur-sm bg-white/50 dark:bg-slate-900/50 rounded-2xl p-8 border border-slate-200 dark:border-slate-800 shadow-lg mb-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
                  Infrastructure
                </h1>
                <p className="text-slate-600 dark:text-slate-400">Monitor droplets and system health in real-time</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Last refresh</p>
                  <p className="text-sm font-mono text-slate-700 dark:text-slate-300">{lastRefresh.toLocaleTimeString()}</p>
                </div>
                <button
                  onClick={() => fetchHealthData(true)}
                  disabled={healthLoading || !canRefresh}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg transition-all flex items-center gap-2 font-medium shadow-lg hover:shadow-xl disabled:cursor-not-allowed"
                >
                  <Activity size={18} className={healthLoading ? 'animate-spin' : ''} />
                  {healthLoading ? 'Refreshing...' : !canRefresh ? 'Wait 5s...' : 'Refresh'}
                </button>
              </div>
            </div>

            {/* Data Quality Info */}
            {stats.rawTotal > stats.total && (
              <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="text-blue-600 dark:text-blue-400 mt-0.5" size={16} />
                  <div className="text-sm">
                    <p className="text-blue-900 dark:text-blue-200 font-medium">
                      Showing {stats.total} unique droplets (deduplicated from {stats.rawTotal} entries)
                    </p>
                    <p className="text-blue-700 dark:text-blue-300 text-xs mt-1">
                      Some droplets have duplicate registrations. Displaying the most complete data for each.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 hover:shadow-lg transition-all duration-300">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg">
                    <Server className="text-white" size={22} />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-black dark:text-white">{stats.total}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Total Droplets</p>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 hover:shadow-lg transition-all duration-300">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg">
                    <Activity className="text-white" size={22} />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-black dark:text-white">{stats.active}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Active</p>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 hover:shadow-lg transition-all duration-300">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl shadow-lg">
                    <Activity className="text-white" size={22} />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-black dark:text-white">{stats.inactive}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Inactive</p>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 hover:shadow-lg transition-all duration-300">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-gradient-to-br from-red-500 to-red-600 rounded-xl shadow-lg">
                    <AlertCircle className="text-white" size={22} />
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-black dark:text-white">{stats.error}</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Error</p>
                  </div>
                </div>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-auto">
            <Card>
              {/* Search and Filters */}
              <div className="mb-6 space-y-4">
                <div className="flex flex-col md:flex-row gap-4">
                  {/* Search */}
                  <div className="flex-1 relative group">
                    <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" size={20} />
                    <input
                      type="text"
                      placeholder="Search by ID, name, host, or role..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-12 pr-4 py-3 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl text-black dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                    />
                  </div>

                  {/* Status Filter */}
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-5 py-3 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer min-w-[140px]"
                  >
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>

                {/* Active Filters Display */}
                {(searchQuery || statusFilter !== 'all') && (
                  <div className="flex items-center gap-2 text-sm flex-wrap">
                    <span className="text-slate-600 dark:text-slate-400 font-medium">Filters:</span>
                    {searchQuery && (
                      <span className="px-3 py-1.5 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-lg font-medium">
                        "{searchQuery}"
                      </span>
                    )}
                    {statusFilter !== 'all' && (
                      <span className="px-3 py-1.5 bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-300 rounded-lg font-medium capitalize">
                        {statusFilter}
                      </span>
                    )}
                    <button
                      onClick={() => {
                        setSearchQuery('');
                        setStatusFilter('all');
                      }}
                      className="px-3 py-1.5 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-all font-medium"
                    >
                      Clear all
                    </button>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-black dark:text-white">
                  Droplets
                  <span className="ml-2 text-slate-500 dark:text-slate-400 font-normal">
                    ({filteredDroplets.length}{filteredDroplets.length !== allDroplets.length ? ` of ${allDroplets.length}` : ''})
                  </span>
                </h3>
              </div>
              
              {(loading || healthLoading) ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="mt-4 text-slate-500">Loading droplets...</p>
                </div>
              ) : filteredDroplets.length === 0 ? (
                <div className="text-center py-12">
                  <AlertCircle className="mx-auto text-slate-400" size={48} />
                  <p className="mt-4 text-slate-500">
                    {allDroplets.length === 0 ? 'No droplets registered' : 'No droplets match your filters'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {filteredDroplets.map((droplet: any) => {
                    const health = healthData[droplet.id] || { available: false };
                    return (
                      <DropletCard 
                        key={droplet.id} 
                        droplet={droplet}
                        health={health}
                        onClick={() => setSelectedDroplet({...droplet, health})}
                      />
                    );
                  })}
                </div>
              )}
            </Card>
          </div>
        </div>
      </main>

      {selectedDroplet && (
        <DropletDetails 
          droplet={selectedDroplet} 
          onClose={() => setSelectedDroplet(null)} 
        />
      )}
    </div>
  );
}

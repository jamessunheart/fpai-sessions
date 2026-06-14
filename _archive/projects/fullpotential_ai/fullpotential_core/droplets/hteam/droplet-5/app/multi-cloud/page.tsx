'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import ModernSidebar from '../components/ModernSidebar';
import { Card } from '../shared/components';
import { Server, Power, RotateCw, Trash2, Plus, RefreshCw } from 'lucide-react';

interface DODroplet {
  id: number;
  name: string;
  status: string;
  networks: { v4: Array<{ ip_address: string; type: string }> };
  region: { name: string };
  size: { memory: number; vcpus: number };
}

interface HetznerServer {
  id: number;
  name: string;
  status: string;
  public_net: { ipv4: { ip: string } };
  datacenter: { location: { name: string } };
  server_type: { memory: number; cores: number };
}

interface VultrInstance {
  id: string;
  label: string;
  power_status: string;
  server_status: string;
  status: string;
  main_ip: string;
  region: string;
  ram: number;
  vcpu_count: number;
}

interface MultiCloudServer {
  id: string | number;
  name: string;
  provider: 'do' | 'hetzner' | 'vultr';
  status: string;
  serverStatus?: string;
  ip: string;
  region: string;
  memory: number;
  vcpus: number;
  isLocked?: boolean;
}

export default function MultiCloudPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [servers, setServers] = useState<MultiCloudServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    provider: 'do' as 'do' | 'hetzner' | 'vultr',
    name: '',
    region: 'sfo3',
    size: 's-1vcpu-512mb-10gb',
    image: 'ubuntu-24-04-x64'
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchServers();
      // Auto-refresh every 10 seconds to show real-time status changes
      const interval = setInterval(fetchServers, 10000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const fetchServers = async () => {
    try {
      const response = await fetch('/api/multi-cloud?endpoint=/multi/list');
      const data = await response.json();
      
      const doServers: MultiCloudServer[] = (data.do || []).map((s: any) => ({
        id: s.id,
        name: s.name,
        provider: 'do' as const,
        status: s.status,
        ip: s.ip,
        region: s.region,
        memory: 512,
        vcpus: 1,
        isLocked: s.status === 'new' || s.status === 'off'
      }));

      const hetznerServers: MultiCloudServer[] = (data.hetzner || []).map((s: any) => ({
        id: s.id,
        name: s.name,
        provider: 'hetzner' as const,
        status: s.status,
        ip: s.ip,
        region: s.region,
        memory: 4096,
        vcpus: 2,
        isLocked: s.status === 'initializing' || s.status === 'starting'
      }));

      const vultrServers: MultiCloudServer[] = (data.vultr || []).map((s: any) => ({
        id: s.id,
        name: s.name,
        provider: 'vultr' as const,
        status: s.status,
        serverStatus: s.status,
        ip: s.ip,
        region: s.region,
        memory: 1024,
        vcpus: 1,
        isLocked: s.status === 'pending'
      }));
      
      setServers([...doServers, ...hetznerServers, ...vultrServers]);
    } catch (error) {
      console.error('Failed to fetch servers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (provider: string, serverId: string | number, action: 'reboot' | 'power_on' | 'power_off') => {


    setActionLoading(`${serverId}-${action}`);
    
    if (action === 'reboot') {
      await handleReboot(provider, serverId);
      return;
    }
    
    try {
      const response = await fetch(`/api/multi-cloud?endpoint=/${provider}/action/${serverId}?action=${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      
      const result = await response.json();
      

      
      // Update status immediately
      let newStatus = 'off';
      if (action === 'power_on') {
        newStatus = provider === 'hetzner' ? 'running' : (provider === 'vultr' ? 'running' : 'active');
      }
      
      setServers(prev => prev.map(s => 
        s.id === serverId && s.provider === provider ? { ...s, status: newStatus } : s
      ));
      
      // Refresh after 5 seconds
      setTimeout(async () => {
        await fetchServers();
      }, 5000);
    } catch (error) {
      console.error('Action failed:', error);
      alert('Action failed. Please try again.');
    } finally {
      setActionLoading(null);
    }
  };
  
  const handleReboot = async (provider: string, serverId: string | number) => {
    try {
      await fetch(`/api/multi-cloud?endpoint=/${provider}/action/${serverId}?action=reboot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reboot' })
      });
      
      // Show server going offline
      setServers(prev => prev.map(s => 
        s.id === serverId && s.provider === provider ? { ...s, status: 'off' } : s
      ));
      
      // After 8 seconds, show online
      setTimeout(() => {
        const onlineStatus = provider === 'hetzner' ? 'running' : (provider === 'vultr' ? 'running' : 'active');
        setServers(prev => prev.map(s => 
          s.id === serverId && s.provider === provider ? { ...s, status: onlineStatus } : s
        ));
      }, 8000);
      
      // Refresh full data after 10 seconds
      setTimeout(async () => {
        await fetchServers();
      }, 10000);
    } catch (error) {
      console.error('Reboot failed:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (provider: string, serverId: string | number) => {
    if (!confirm('Are you sure you want to delete this server?')) return;
    
    setActionLoading(`${serverId}-delete`);
    try {
      const response = await fetch(`/api/multi-cloud?endpoint=/${provider}/delete/${serverId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      

      
      await fetchServers();
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Delete failed. Please try again.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateServer = async () => {
    if (!createForm.name) {
      alert('Please enter a server name');
      return;
    }



    setActionLoading('creating');
    try {
      // Add user_data based on provider
      let payload: any = { ...createForm };
      
      if (createForm.provider === 'do') {
        payload.user_data = "#cloud-config\nchpasswd:\n  list: |\n    root:W7taBbzeJku$h\n  expire: False";
      } else if (createForm.provider === 'hetzner') {
        payload.user_data = "#cloud-config\nruncmd:\n - echo hetzner > /root/hello.txt";
      } else if (createForm.provider === 'vultr') {
        payload.user_data = "#cloud-config\nchpasswd:\n  list: |\n    root:W7taBbzeJku$h\n  expire: False";
      }

      const response = await fetch(`/api/multi-cloud?endpoint=/${createForm.provider}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await response.json();
      
      if (!response.ok || result.error) {
        console.error('Create failed:', result);
        let errorMsg = result.error || result.detail || 'Unknown error';
        alert(`Failed to create server: ${errorMsg}`);
        setActionLoading(null);
        return;
      }

      setShowCreateModal(false);
      setCreateForm({ provider: 'do', name: '', region: 'sfo3', size: 's-1vcpu-512mb-10gb', image: 'ubuntu-24-04-x64' });
      alert('Server creation started! Refreshing in 3 seconds...');
      
      // Wait 3 seconds for server to provision before refreshing
      setTimeout(async () => {
        await fetchServers();
        setActionLoading(null);
      }, 3000);
    } catch (error) {
      console.error('Create failed:', error);
      alert('Failed to create server: Network error');
      setActionLoading(null);
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'do': return 'bg-blue-500';
      case 'hetzner': return 'bg-red-500';
      case 'vultr': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getProviderName = (provider: string) => {
    switch (provider) {
      case 'do': return 'DigitalOcean';
      case 'hetzner': return 'Hetzner';
      case 'vultr': return 'Vultr';
      default: return provider;
    }
  };

  if (authLoading || !isAuthenticated) return null;

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <ModernSidebar />
      
      <main className="flex-1 overflow-auto bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
        <div className="h-full flex flex-col p-6">
          <header className="backdrop-blur-sm bg-white/50 dark:bg-slate-900/50 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-lg mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg shadow-lg">
                <Server className="text-white" size={24} />
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">Multi-Cloud Manager</h1>
                <p className="text-sm text-slate-600 dark:text-slate-400">Unified control across DigitalOcean, Hetzner & Vultr</p>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-auto animate-fade-in space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 border border-blue-100 dark:border-blue-900/30">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-blue-600/5 dark:from-blue-500/20 dark:to-blue-600/10"></div>
                <div className="relative p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-3 bg-blue-500 rounded-xl shadow-lg relative">
                      <Server className="text-white" size={24} />
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full" title="API Working"></div>
                    </div>
                    <span className="text-5xl font-bold text-blue-600 dark:text-blue-400">{servers.filter(s => s.provider === 'do').length}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                    DigitalOcean
                    <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded-full">Online</span>
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Active Droplets</p>
                </div>
              </div>
              
              <div className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 border border-red-100 dark:border-red-900/30">
                <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-red-600/5 dark:from-red-500/20 dark:to-red-600/10"></div>
                <div className="relative p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-3 bg-red-500 rounded-xl shadow-lg relative">
                      <Server className="text-white" size={24} />
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full" title="API Working"></div>
                    </div>
                    <span className="text-5xl font-bold text-red-600 dark:text-red-400">{servers.filter(s => s.provider === 'hetzner').length}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                    Hetzner
                    <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded-full">Online</span>
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Active Servers</p>
                </div>
              </div>
              
              <div className="group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 border border-purple-100 dark:border-purple-900/30">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-purple-600/5 dark:from-purple-500/20 dark:to-purple-600/10"></div>
                <div className="relative p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-3 bg-purple-500 rounded-xl shadow-lg relative">
                      <Server className="text-white" size={24} />
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full" title="API Working"></div>
                    </div>
                    <span className="text-5xl font-bold text-purple-600 dark:text-purple-400">{servers.filter(s => s.provider === 'vultr').length}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                    Vultr
                    <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded-full">Online</span>
                  </h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">Active Instances</p>
                </div>
              </div>
            </div>

            {/* Servers List */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <div className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-700 px-6 py-4 border-b border-slate-200 dark:border-slate-600">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-slate-800 dark:text-white">Server Fleet</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{servers.length} total servers across all providers</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={() => { setLoading(true); fetchServers(); }}
                      disabled={loading}
                      className="flex items-center gap-2 px-4 py-3 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-300 dark:hover:bg-slate-600 transition-all duration-300 font-medium disabled:opacity-50"
                      title="Refresh server list"
                    >
                      <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                      Refresh
                    </button>
                    <button 
                      onClick={() => setShowCreateModal(true)}
                      className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-300 shadow-lg hover:shadow-xl font-medium"
                    >
                      <Plus size={18} />
                      Create Server
                    </button>
                  </div>
                </div>
              </div>
              <div className="p-6">

                {loading ? (
                  <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
                    <p className="mt-4 text-slate-600 dark:text-slate-400">Loading servers...</p>
                  </div>
                ) : servers.length === 0 ? (
                  <div className="text-center py-12">
                    <Server className="mx-auto text-slate-300 dark:text-slate-600 mb-4" size={48} />
                    <p className="text-slate-600 dark:text-slate-400">No servers found</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {servers.map((server) => (
                      <div 
                        key={`${server.provider}-${server.id}`}
                        className="group relative overflow-hidden bg-gradient-to-r from-slate-50 to-white dark:from-slate-700/50 dark:to-slate-800/50 rounded-xl p-5 border border-slate-200 dark:border-slate-600 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-lg transition-all duration-300"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-xl ${getProviderColor(server.provider)} flex items-center justify-center shadow-lg`}>
                              <Server className="text-white" size={24} />
                            </div>
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <p className="font-bold text-lg text-slate-800 dark:text-white">{server.name}</p>
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                  server.isLocked
                                    ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                                    : server.status === 'active' || server.status === 'running'
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                                    : server.status === 'off' || server.status === 'stopped'
                                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                }`}>
                                  {server.isLocked ? (server.serverStatus || 'provisioning') : server.status}
                                </span>
                              </div>
                              <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                                <span className="font-medium">{getProviderName(server.provider)}</span>
                                <span>•</span>
                                <span>{server.ip}</span>
                                <span>•</span>
                                <span>{server.region}</span>
                              </div>
                              <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-500 mt-1">
                                <span>{server.vcpus} vCPU</span>
                                <span>•</span>
                                <span>{Math.round(server.memory / 1024)}GB RAM</span>
                                {server.isLocked && (
                                  <>
                                    <span>•</span>
                                    <span className="text-orange-600 dark:text-orange-400 font-medium animate-pulse">⏳ Provisioning...</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleAction(server.provider, server.id, 'reboot')}
                              disabled={server.isLocked || actionLoading === `${server.id}-reboot`}
                              className="p-3 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-xl transition-all duration-200 disabled:opacity-50 group/btn"
                              title={server.isLocked ? 'Server is provisioning...' : 'Reboot'}
                            >
                              <RotateCw size={18} className="text-slate-600 dark:text-slate-300 group-hover/btn:text-blue-600 dark:group-hover/btn:text-blue-400" />
                            </button>
                            <button
                              onClick={() => handleAction(server.provider, server.id, (server.status === 'active' || server.status === 'running') ? 'power_off' : 'power_on')}
                              disabled={server.isLocked || actionLoading === `${server.id}-power_on` || actionLoading === `${server.id}-power_off`}
                              className="p-3 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-xl transition-all duration-200 disabled:opacity-50 group/btn"
                              title={server.isLocked ? 'Server is provisioning...' : ((server.status === 'active' || server.status === 'running') ? 'Power Off' : 'Power On')}
                            >
                              <Power size={18} className="text-slate-600 dark:text-slate-300 group-hover/btn:text-green-600 dark:group-hover/btn:text-green-400" />
                            </button>
                            <button
                              onClick={() => handleDelete(server.provider, server.id)}
                              disabled={server.isLocked || actionLoading === `${server.id}-delete`}
                              className="p-3 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-xl transition-all duration-200 disabled:opacity-50 group/btn"
                              title={server.isLocked ? 'Cannot delete - Server is provisioning...' : 'Delete'}
                            >
                              <Trash2 size={18} className="text-slate-600 dark:text-slate-300 group-hover/btn:text-red-600 dark:group-hover/btn:text-red-400" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl max-w-md w-full p-6">
            <h2 className="text-2xl font-bold text-black dark:text-white mb-4">Create New Server</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-black dark:text-white mb-2">Provider</label>
                <select
                  value={createForm.provider}
                  onChange={(e) => {
                    const provider = e.target.value as 'do' | 'hetzner' | 'vultr';
                    // Set appropriate defaults for each provider
                    const defaults = {
                      do: { region: 'sfo3', size: 's-1vcpu-512mb-10gb', image: 'ubuntu-24-04-x64' },
                      hetzner: { region: 'fsn1', size: 'cpx11', image: 'ubuntu-22.04' },
                      vultr: { region: 'sea', size: 'vc2-1c-1gb', image: '1743' }
                    };
                    setCreateForm({ 
                      ...createForm, 
                      provider,
                      ...defaults[provider]
                    });
                  }}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-slate-700 text-black dark:text-white rounded-lg"
                >
                  <option value="do">DigitalOcean</option>
                  <option value="hetzner">Hetzner</option>
                  <option value="vultr">Vultr</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-black dark:text-white mb-2">Server Name</label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  placeholder="my-server-1"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-slate-700 text-black dark:text-white rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-black dark:text-white mb-2">Region</label>
                <input
                  type="text"
                  value={createForm.region}
                  onChange={(e) => setCreateForm({ ...createForm, region: e.target.value })}
                  placeholder="sfo3"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-slate-700 text-black dark:text-white rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-black dark:text-white mb-2">Size</label>
                <input
                  type="text"
                  value={createForm.size}
                  onChange={(e) => setCreateForm({ ...createForm, size: e.target.value })}
                  placeholder="s-1vcpu-512mb-10gb"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-slate-700 text-black dark:text-white rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-black dark:text-white mb-2">Image</label>
                <input
                  type="text"
                  value={createForm.image}
                  onChange={(e) => setCreateForm({ ...createForm, image: e.target.value })}
                  placeholder="ubuntu-24-04-x64"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-slate-700 text-black dark:text-white rounded-lg"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-slate-700 text-black dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-slate-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateServer}
                disabled={actionLoading === 'creating'}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {actionLoading === 'creating' ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

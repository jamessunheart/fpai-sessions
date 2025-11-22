'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../shared/contexts/AuthContext';
import { useApi } from '../shared/hooks/useApi';
import { api } from '../lib/api';
import ModernSidebar from '../components/ModernSidebar';
import { Send, Paperclip, Search, ArrowDown, Check, CheckCheck, Menu, X } from 'lucide-react';
import VoiceRecorder from '../components/VoiceRecorder';

interface Droplet {
  id: number;
  cloudId: number;
  name: string;
  provider: 'do' | 'hetzner' | 'vultr';
  powerStatus: string;
  heartbeatStatus: 'live' | 'warning' | 'down';
  lastSeen: number | null;
  ip: string;
  region: string;
  cpu: number | null;
  mem: number | null;
  specs?: string;
  cost?: number;
}

export default function ChatPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  
  const [droplets, setDroplets] = useState<Droplet[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDroplet, setSelectedDroplet] = useState<Droplet | null>(null);
  const [message, setMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [messages, setMessages] = useState<Array<{id: number, text: string, type: 'user' | 'system', timestamp: Date}>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fetchMergedData = async () => {
    setIsRefreshing(true);
    try {
      const multiCloudRes = await fetch('/api/multi-cloud?endpoint=/multi/list');
      if (!multiCloudRes.ok) throw new Error('Multi-cloud API failed');
      const multiCloud = await multiCloudRes.json();

      const merged: Droplet[] = [];
      let idCounter = 1;

      // Process DO droplets
      (multiCloud.do || []).map((s: any) => {
        merged.push({
          id: idCounter++,
          cloudId: s.id,
          name: s.name,
          provider: 'do',
          powerStatus: s.status,
          heartbeatStatus: s.status === 'active' ? 'live' : 'down',
          lastSeen: null,
          ip: s.ip,
          region: s.region,
          cpu: null,
          mem: null,
          specs: '1vCPU, 512MB RAM',
          cost: 0.006
        });
      });

      // Process Hetzner servers
      (multiCloud.hetzner || []).map((s: any) => {
        merged.push({
          id: idCounter++,
          cloudId: s.id,
          name: s.name,
          provider: 'hetzner',
          powerStatus: s.status,
          heartbeatStatus: s.status === 'running' ? 'live' : 'down',
          lastSeen: null,
          ip: s.ip,
          region: s.region,
          cpu: null,
          mem: null,
          specs: '2vCPU, 4GB RAM',
          cost: 0.01
        });
      });

      // Process Vultr instances
      (multiCloud.vultr || []).map((s: any) => {
        merged.push({
          id: idCounter++,
          cloudId: s.id,
          name: s.name,
          provider: 'vultr',
          powerStatus: s.status,
          heartbeatStatus: s.status === 'active' ? 'live' : 'down',
          lastSeen: null,
          ip: s.ip,
          region: s.region,
          cpu: null,
          mem: null,
          specs: '1vCPU, 1GB RAM',
          cost: 0.01
        });
      });

      setDroplets(merged);
    } catch (error) {
      console.error('❌ Failed to fetch data:', error);
      setDroplets([]);
    } finally {
      setDataLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchMergedData();
      const interval = setInterval(fetchMergedData, 30000); // Update every 30 seconds to avoid rate limits
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [message]);

  useEffect(() => {
    scrollToBottom();
  }, [selectedDroplet]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (droplets.length > 0 && !selectedDroplet) {
      setSelectedDroplet(droplets[0]);
    }
  }, [droplets, selectedDroplet]);

  useEffect(() => {
    // Clear messages when switching droplets
    setMessages([]);
  }, [selectedDroplet?.id]);

  if (authLoading || !isAuthenticated) return null;

  const filteredDroplets = droplets.filter(d => 
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.region.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.ip.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getHeartbeatColor = (status: string) => {
    if (status === 'live') return 'bg-green-500';
    if (status === 'warning') return 'bg-yellow-500';
    return 'bg-gray-400';
  };

  const getPowerStatusColor = (status: string) => {
    if (status === 'active' || status === 'running') return 'text-green-600 dark:text-green-400';
    return 'text-gray-400';
  };

  const getTimeAgo = (timestamp: number | null) => {
    if (!timestamp) return 'Never';
    const now = Math.floor(Date.now() / 1000);
    const diff = now - timestamp;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const handleSendMessage = async () => {
    if (!message.trim() || !selectedDroplet) return;
    
    const userMessage = message.trim();
    const cmd = userMessage.toLowerCase();
    
    // Add user message to chat
    const userMsg = { id: Date.now(), text: userMessage, type: 'user' as const, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    
    // Clear input immediately
    setMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    // Parse commands (handle both exact matches and voice commands)
    if (cmd.includes('reboot') || cmd.includes('restart')) {
      await executeReboot(userMessage);
    } else if (cmd.includes('power off') || cmd.includes('poweroff') || cmd.includes('shutdown') || cmd.includes('stop')) {
      await executeCommand('power_off', userMessage);
    } else if (cmd.includes('power on') || cmd.includes('poweron') || cmd.includes('start') || cmd.includes('boot')) {
      await executeCommand('power_on', userMessage);
    } else if (cmd.includes('delete') || cmd.includes('destroy') || cmd.includes('remove')) {
      await executeDelete(userMessage);
    } else if (cmd.includes('confirm delete')) {
      await executeConfirmDelete();
    } else if (cmd.includes('status') || cmd.includes('info') || cmd.includes('check')) {
      // Add status command
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        text: `📊 ${selectedDroplet.name} Status:\n• Power: ${selectedDroplet.powerStatus}\n• IP: ${selectedDroplet.ip}\n• Region: ${selectedDroplet.region}\n• Provider: ${selectedDroplet.provider}`, 
        type: 'system', 
        timestamp: new Date() 
      }]);
    } else {
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        text: '❌ Unknown command. Available: reboot, power off, power on, delete, status', 
        type: 'system', 
        timestamp: new Date() 
      }]);
    }
    
    scrollToBottom();
  };

  const executeReboot = async (originalCmd: string) => {
    if (!selectedDroplet) return;
    
    // Show rebooting message
    setMessages(prev => [...prev, { 
      id: Date.now() + 1, 
      text: `⏳ Rebooting ${selectedDroplet.name}...`, 
      type: 'system', 
      timestamp: new Date() 
    }]);
    
    try {
      const response = await fetch(`/api/multi-cloud?endpoint=/${selectedDroplet.provider}/action/${selectedDroplet.cloudId}?action=reboot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reboot' })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        // Show server going offline
        setMessages(prev => [...prev, { 
          id: Date.now() + 2, 
          text: `🔴 ${selectedDroplet.name} is shutting down...`, 
          type: 'system', 
          timestamp: new Date() 
        }]);
        
        // Update status to offline
        setSelectedDroplet(prev => prev ? { ...prev, powerStatus: 'off' } : null);
        setDroplets(prev => prev.map(d => 
          d.id === selectedDroplet.id ? { ...d, powerStatus: 'off' } : d
        ));
        
        // After 3 seconds, show booting up
        setTimeout(() => {
          setMessages(prev => [...prev, { 
            id: Date.now() + 3, 
            text: `🟡 ${selectedDroplet.name} is booting up...`, 
            type: 'system', 
            timestamp: new Date() 
          }]);
        }, 3000);
        
        // After 8 seconds, show online
        setTimeout(() => {
          const onlineStatus = selectedDroplet.provider === 'hetzner' ? 'running' : 'active';
          setSelectedDroplet(prev => prev ? { ...prev, powerStatus: onlineStatus } : null);
          setDroplets(prev => prev.map(d => 
            d.id === selectedDroplet.id ? { ...d, powerStatus: onlineStatus } : d
          ));
          
          setMessages(prev => [...prev, { 
            id: Date.now() + 4, 
            text: `✅ ${selectedDroplet.name} is back online`, 
            type: 'system', 
            timestamp: new Date() 
          }]);
        }, 8000);
        
        // Refresh full data after 3 seconds
        setTimeout(() => fetchMergedData(), 3000);
      } else {
        setMessages(prev => [...prev, { 
          id: Date.now() + 2, 
          text: `❌ Reboot failed: ${result.error || 'Unknown error'}`, 
          type: 'system', 
          timestamp: new Date() 
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        id: Date.now() + 2, 
        text: '❌ Failed to execute reboot', 
        type: 'system', 
        timestamp: new Date() 
      }]);
    }
  };

  const executeDelete = async (originalCmd: string) => {
    if (!selectedDroplet) return;
    
    // Show confirmation message
    setMessages(prev => [...prev, { 
      id: Date.now() + 1, 
      text: `⚠️ Are you sure you want to delete ${selectedDroplet.name}? This action cannot be undone. Type 'confirm delete' to proceed.`, 
      type: 'system', 
      timestamp: new Date() 
    }]);
  };

  const executeConfirmDelete = async () => {
    if (!selectedDroplet) return;
    
    // Show deleting message
    setMessages(prev => [...prev, { 
      id: Date.now() + 1, 
      text: `🗑️ Deleting ${selectedDroplet.name}...`, 
      type: 'system', 
      timestamp: new Date() 
    }]);
    
    try {
      const response = await fetch(`/api/multi-cloud?endpoint=/${selectedDroplet.provider}/delete/${selectedDroplet.cloudId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setMessages(prev => [...prev, { 
          id: Date.now() + 2, 
          text: `✅ ${selectedDroplet.name} has been successfully deleted`, 
          type: 'system', 
          timestamp: new Date() 
        }]);
        
        // Remove from droplets list
        setDroplets(prev => prev.filter(d => d.id !== selectedDroplet.id));
        
        // Select another droplet or clear selection
        const remainingDroplets = droplets.filter(d => d.id !== selectedDroplet.id);
        if (remainingDroplets.length > 0) {
          setSelectedDroplet(remainingDroplets[0]);
        } else {
          setSelectedDroplet(null);
        }
        
        // Refresh data after 1 second
        setTimeout(() => fetchMergedData(), 1000);
      } else {
        setMessages(prev => [...prev, { 
          id: Date.now() + 2, 
          text: `❌ Delete failed: ${result.error || 'Unknown error'}`, 
          type: 'system', 
          timestamp: new Date() 
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        id: Date.now() + 2, 
        text: '❌ Failed to delete server', 
        type: 'system', 
        timestamp: new Date() 
      }]);
    }
  };

  const executeCommand = async (action: 'power_on' | 'power_off', originalCmd: string) => {
    if (!selectedDroplet) return;
    
    // Show executing message
    setMessages(prev => [...prev, { 
      id: Date.now() + 2, 
      text: `⏳ Executing ${action.replace('_', ' ')}...`, 
      type: 'system', 
      timestamp: new Date() 
    }]);
    
    try {
      const response = await fetch(`/api/multi-cloud?endpoint=/${selectedDroplet.provider}/action/${selectedDroplet.cloudId}?action=${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setMessages(prev => [...prev, { 
          id: Date.now() + 3, 
          text: `✅ ${action.replace('_', ' ')} executed successfully on ${selectedDroplet.name}`, 
          type: 'system', 
          timestamp: new Date() 
        }]);
        
        // Update status immediately in both selected droplet and droplets list
        const newStatus = action === 'power_off' ? 'off' : action === 'power_on' ? (selectedDroplet.provider === 'hetzner' ? 'running' : 'active') : selectedDroplet.powerStatus;
        
        setSelectedDroplet(prev => prev ? { ...prev, powerStatus: newStatus } : null);
        setDroplets(prev => prev.map(d => 
          d.id === selectedDroplet.id ? { ...d, powerStatus: newStatus } : d
        ));
        
        // Refresh full data after 2 seconds
        setTimeout(() => fetchMergedData(), 2000);
      } else {
        setMessages(prev => [...prev, { 
          id: Date.now() + 3, 
          text: `❌ Command failed: ${result.error || 'Unknown error'}`, 
          type: 'system', 
          timestamp: new Date() 
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        id: Date.now() + 3, 
        text: '❌ Failed to execute command', 
        type: 'system', 
        timestamp: new Date() 
      }]);
    }
  };

  return (
    <div className="flex h-screen bg-white dark:bg-slate-900">
      <ModernSidebar />
      
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Premium Header */}
        <div className="px-6 py-5 border-b border-gray-200/60 dark:border-slate-700/60 bg-white/95 dark:bg-slate-800/95 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
                <Send className="text-white" size={16} />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Server Console
                </h1>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">Manage your infrastructure</p>
              </div>
            </div>
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="lg:hidden p-2.5 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-xl transition-all duration-200 hover:scale-105"
            >
              {isSidebarOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Premium Chat Container */}
        <div className="flex-1 flex overflow-hidden relative">
          {/* Premium Droplet Sidebar */}
          <div className={`${
            isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
          } lg:translate-x-0 absolute lg:relative z-20 w-72 h-full border-r border-gray-200/60 dark:border-slate-700/60 flex flex-col bg-white/98 dark:bg-slate-800/98 backdrop-blur-xl transition-transform duration-300 ease-out shadow-2xl lg:shadow-none`}>
            {/* Premium Search */}
            <div className="p-4 border-b border-gray-200/60 dark:border-slate-700/60">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" size={16} />
                <input
                  type="text"
                  placeholder="Search servers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50/80 dark:bg-slate-700/30 border border-gray-200/80 dark:border-slate-600/50 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/60 transition-all duration-200"
                />
              </div>
            </div>

            {/* Premium Droplet List */}
            <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600">
              {dataLoading ? (
                <div className="p-3 space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-14 bg-gradient-to-r from-gray-100/60 to-gray-50/60 dark:from-slate-700/40 dark:to-slate-700/20 rounded-lg animate-pulse"></div>
                  ))}
                </div>
              ) : filteredDroplets.length === 0 ? (
                <div className="p-6 text-center">
                  <div className="w-10 h-10 bg-gray-100/80 dark:bg-slate-700/50 rounded-lg flex items-center justify-center mx-auto mb-2">
                    <Search className="text-gray-400" size={16} />
                  </div>
                  <p className="text-sm text-gray-500 dark:text-slate-400">No servers found</p>
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {filteredDroplets.map((droplet, index) => (
                    <button
                      key={droplet.id}
                      onClick={() => { setSelectedDroplet(droplet); setIsSidebarOpen(false); }}
                      style={{ animationDelay: `${index * 20}ms` }}
                      className={`w-full p-3 flex items-center gap-3 rounded-lg transition-all duration-200 group animate-fade-in ${
                        selectedDroplet?.id === droplet.id 
                          ? 'bg-blue-50/80 dark:bg-blue-900/20 shadow-sm border border-blue-200/50 dark:border-blue-700/50' 
                          : 'hover:bg-gray-50/80 dark:hover:bg-slate-700/30 hover:shadow-sm'
                      }`}
                    >
                      {/* Premium Avatar */}
                      <div className="relative flex-shrink-0">
                        <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${
                          droplet.provider === 'do' ? 'from-blue-500 to-blue-600' : 
                          droplet.provider === 'hetzner' ? 'from-red-500 to-red-600' : 'from-purple-500 to-purple-600'
                        } flex items-center justify-center text-white text-xs font-semibold shadow-sm`}>
                          {droplet.provider === 'do' ? 'DO' : droplet.provider === 'hetzner' ? 'HZ' : 'VT'}
                        </div>
                        <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 ${getHeartbeatColor(droplet.heartbeatStatus)} rounded-full border-2 border-white dark:border-slate-800 shadow-sm ${
                          droplet.heartbeatStatus === 'live' ? 'animate-pulse' : ''
                        }`}></div>
                      </div>

                      {/* Premium Info */}
                      <div className="flex-1 text-left min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="font-medium text-sm text-gray-900 dark:text-white truncate">
                            {droplet.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs">
                          <div className={`w-1.5 h-1.5 rounded-full ${
                            droplet.powerStatus === 'active' || droplet.powerStatus === 'running' ? 'bg-green-500' : 'bg-gray-400'
                          }`}></div>
                          <span className={droplet.powerStatus === 'active' || droplet.powerStatus === 'running' ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}>
                            {droplet.powerStatus === 'active' || droplet.powerStatus === 'running' ? 'Online' : 'Offline'}
                          </span>
                          {droplet.heartbeatStatus === 'warning' && (
                            <span className="text-amber-500">⚠</span>
                          )}
                          {droplet.heartbeatStatus === 'down' && (
                            <span className="text-red-500">⚠</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 truncate">
                          {getTimeAgo(droplet.lastSeen)}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Premium Stats Footer */}
            <div className="p-3 border-t border-gray-200/60 dark:border-slate-700/60 bg-gray-50/50 dark:bg-slate-800/30">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white/80 dark:bg-slate-700/30 rounded-lg p-2 border border-gray-200/60 dark:border-slate-600/40">
                  <div className="text-xs text-gray-500 dark:text-slate-400">Total</div>
                  <div className="text-base font-semibold text-gray-900 dark:text-white">{droplets.length}</div>
                </div>
                <div className="bg-green-50/80 dark:bg-green-900/20 rounded-lg p-2 border border-green-200/60 dark:border-green-700/40">
                  <div className="text-xs text-green-700 dark:text-green-400">Online</div>
                  <div className="text-base font-semibold text-green-900 dark:text-green-300">
                    {droplets.filter(d => d.powerStatus === 'active' || d.powerStatus === 'running').length}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Overlay for mobile */}
          {isSidebarOpen && (
            <div 
              className="lg:hidden absolute inset-0 bg-black/20 backdrop-blur-sm z-10"
              onClick={() => setIsSidebarOpen(false)}
            />
          )}

          {/* Premium Chat Area */}
          <div className="flex-1 flex flex-col bg-gray-50/50 dark:bg-slate-900/50">
            {selectedDroplet ? (
              <>
                {/* Premium Chat Header */}
                <div className="px-5 py-4 bg-white/95 dark:bg-slate-800/95 backdrop-blur-xl border-b border-gray-200/60 dark:border-slate-700/60 animate-fade-in">
                  <div className="flex items-center gap-3">
                    <div className="relative flex-shrink-0">
                      <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${
                        selectedDroplet.provider === 'do' ? 'from-blue-500 to-blue-600' : 
                        selectedDroplet.provider === 'hetzner' ? 'from-red-500 to-red-600' : 'from-purple-500 to-purple-600'
                      } flex items-center justify-center text-white font-semibold shadow-sm`}>
                        {selectedDroplet.provider === 'do' ? 'DO' : selectedDroplet.provider === 'hetzner' ? 'HZ' : 'VT'}
                      </div>
                      <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 ${getHeartbeatColor(selectedDroplet.heartbeatStatus)} rounded-full border-2 border-white dark:border-slate-800 shadow-sm ${
                        selectedDroplet.heartbeatStatus === 'live' ? 'animate-pulse' : ''
                      }`}></div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="font-semibold text-base text-gray-900 dark:text-white truncate">{selectedDroplet.name}</h2>
                        <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-slate-700 rounded text-gray-600 dark:text-slate-400 uppercase font-medium">
                          {selectedDroplet.provider === 'do' ? 'DigitalOcean' : selectedDroplet.provider === 'hetzner' ? 'Hetzner' : 'Vultr'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <div className={`w-1.5 h-1.5 rounded-full ${
                          selectedDroplet.powerStatus === 'active' || selectedDroplet.powerStatus === 'running' ? 'bg-green-500' : 'bg-gray-400'
                        }`}></div>
                        <span className={selectedDroplet.powerStatus === 'active' || selectedDroplet.powerStatus === 'running' ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}>
                          {selectedDroplet.powerStatus === 'active' || selectedDroplet.powerStatus === 'running' ? 'Online' : 'Offline'}
                        </span>
                        <span className="text-gray-300 dark:text-slate-600">•</span>
                        <span className={
                          selectedDroplet.heartbeatStatus === 'live' ? 'text-green-600 dark:text-green-400' : 
                          selectedDroplet.heartbeatStatus === 'warning' ? 'text-amber-600 dark:text-amber-400' : 
                          'text-red-600 dark:text-red-400'
                        }>
                          {selectedDroplet.heartbeatStatus === 'live' ? 'Connected' : 
                           selectedDroplet.heartbeatStatus === 'warning' ? 'Warning' : 'Disconnected'}
                        </span>
                        {isRefreshing && (
                          <>
                            <span className="text-gray-300 dark:text-slate-600">•</span>
                            <span className="text-blue-500 text-xs animate-pulse">🔄 Refreshing...</span>
                          </>
                        )}
                      </div>
                    </div>
                    {selectedDroplet.cpu && selectedDroplet.mem && (
                      <div className="hidden sm:flex items-center gap-2">
                        <div className="text-center px-2 py-1 bg-gray-100/80 dark:bg-slate-700/50 rounded-lg">
                          <div className="text-xs text-gray-500 dark:text-slate-400">CPU</div>
                          <div className="text-xs font-semibold text-gray-900 dark:text-white">{selectedDroplet.cpu}%</div>
                        </div>
                        <div className="text-center px-2 py-1 bg-gray-100/80 dark:bg-slate-700/50 rounded-lg">
                          <div className="text-xs text-gray-500 dark:text-slate-400">RAM</div>
                          <div className="text-xs font-semibold text-gray-900 dark:text-white">{selectedDroplet.mem}%</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Premium Messages Area */}
                <div className="flex-1 overflow-y-auto px-5 py-6 space-y-3">
                  {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full animate-fade-in">
                      <div className="text-center max-w-sm">
                        <div className="w-16 h-16 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 rounded-xl flex items-center justify-center mx-auto mb-4 border border-blue-200/50 dark:border-blue-800/50">
                          <Send className="text-blue-600 dark:text-blue-400" size={20} />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                          Ready to control {selectedDroplet.name}
                        </h3>
                        <div className="bg-gray-50 dark:bg-slate-800/50 rounded-lg p-4 mb-4 space-y-2">
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <span className="text-gray-500 dark:text-slate-400">Provider:</span>
                              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                                {selectedDroplet.provider === 'do' ? 'DigitalOcean' : selectedDroplet.provider === 'hetzner' ? 'Hetzner' : 'Vultr'}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-500 dark:text-slate-400">Region:</span>
                              <span className="ml-2 font-medium text-gray-900 dark:text-white">{selectedDroplet.region}</span>
                            </div>
                            <div>
                              <span className="text-gray-500 dark:text-slate-400">IP Address:</span>
                              <span className="ml-2 font-mono text-blue-600 dark:text-blue-400">{selectedDroplet.ip}</span>
                            </div>
                            <div>
                              <span className="text-gray-500 dark:text-slate-400">Specs:</span>
                              <span className="ml-2 font-medium text-gray-900 dark:text-white">{selectedDroplet.specs}</span>
                            </div>
                            {selectedDroplet.cost && (
                              <div className="col-span-2">
                                <span className="text-gray-500 dark:text-slate-400">Cost:</span>
                                <span className="ml-2 font-medium text-green-600 dark:text-green-400">${selectedDroplet.cost.toFixed(4)}/hour</span>
                              </div>
                            )}
                          </div>
                        </div>
                        <p className="text-gray-500 dark:text-slate-400 text-sm mb-4">
                          Send commands to manage this server
                        </p>
                        <div className="flex items-center justify-center gap-2 px-3 py-1.5 bg-gray-100/80 dark:bg-slate-700/50 rounded-lg text-xs text-gray-600 dark:text-slate-400">
                          <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                          Console ready
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      {messages.map((msg, index) => (
                        <div 
                          key={msg.id}
                          className={`flex animate-fade-in ${
                            msg.type === 'user' ? 'justify-end' : 'justify-start'
                          }`}
                          style={{ animationDelay: `${index * 30}ms` }}
                        >
                          <div className={`max-w-[75%] ${
                            msg.type === 'user' 
                              ? 'bg-blue-600 text-white' 
                              : 'bg-white dark:bg-slate-700/80 text-gray-900 dark:text-white border border-gray-200/60 dark:border-slate-600/50'
                          } rounded-xl px-3 py-2 shadow-sm`}>
                            <p className="text-sm leading-relaxed">{msg.text}</p>
                            <p className={`text-xs mt-1 opacity-70 ${
                              msg.type === 'user' 
                                ? 'text-blue-100' 
                                : 'text-gray-400 dark:text-slate-400'
                            }`}>
                              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Scroll to Bottom Button */}
                {showScrollButton && (
                  <button
                    onClick={scrollToBottom}
                    className="absolute bottom-24 right-8 p-3 bg-white dark:bg-slate-700 rounded-full shadow-lg border border-gray-200 dark:border-slate-600 hover:scale-110 transition-transform duration-200"
                  >
                    <ArrowDown size={20} className="text-gray-600 dark:text-slate-400" />
                  </button>
                )}

                {/* Premium Message Input */}
                <div className="px-5 py-4 bg-white/95 dark:bg-slate-800/95 backdrop-blur-xl border-t border-gray-200/60 dark:border-slate-700/60">
                  <div className="flex items-end gap-2">
                    <div className="flex-1 relative">
                      <textarea
                        ref={textareaRef}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSendMessage();
                          }
                        }}
                        placeholder="Type a command or use voice..."
                        rows={1}
                        className="w-full px-3 py-2.5 text-sm bg-gray-100/80 dark:bg-slate-700/50 border border-gray-200/80 dark:border-slate-600/50 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/60 resize-none transition-all max-h-24"
                        style={{ minHeight: '40px' }}
                      />
                    </div>
                    <VoiceRecorder 
                      onVoiceCommand={(result) => {
                        // Add voice command result to chat (don't execute again)
                        const userMsg = { 
                          id: Date.now(), 
                          text: `🎤 "${result.transcript}"`, 
                          type: 'user' as const, 
                          timestamp: new Date() 
                        };
                        
                        const systemMsg = {
                          id: Date.now() + 1,
                          text: result.result.status === 'success' 
                            ? `✅ ${result.result.message}` 
                            : `❌ ${result.result.message}`,
                          type: 'system' as const,
                          timestamp: new Date()
                        };
                        
                        setMessages(prev => [...prev, userMsg, systemMsg]);
                        
                        // Immediately update UI state for successful commands
                        if (result.result.status === 'success' && selectedDroplet) {
                          const action = result.transcript.toLowerCase();
                          let newStatus = selectedDroplet.powerStatus;
                          
                          if (action.includes('power off') || action.includes('shutdown')) {
                            newStatus = 'off';
                          } else if (action.includes('power on') || action.includes('start')) {
                            newStatus = selectedDroplet.provider === 'hetzner' ? 'running' : 'active';
                          } else if (action.includes('reboot')) {
                            // For reboot, show offline first, then online after delay
                            newStatus = 'off';
                            setTimeout(() => {
                              const onlineStatus = selectedDroplet.provider === 'hetzner' ? 'running' : 'active';
                              setSelectedDroplet(prev => prev ? { ...prev, powerStatus: onlineStatus } : null);
                              setDroplets(prev => prev.map(d => 
                                d.id === selectedDroplet.id ? { ...d, powerStatus: onlineStatus } : d
                              ));
                            }, 8000);
                          }
                          
                          // Update both selected droplet and droplets list immediately
                          setSelectedDroplet(prev => prev ? { ...prev, powerStatus: newStatus } : null);
                          setDroplets(prev => prev.map(d => 
                            d.id === selectedDroplet.id ? { ...d, powerStatus: newStatus } : d
                          ));
                          
                          // Refresh real data from APIs immediately
                          fetchMergedData();
                          
                          // Continue refreshing every 1 second for 20 seconds to catch status changes
                          let refreshCount = 0;
                          const quickRefresh = setInterval(() => {
                            fetchMergedData();
                            refreshCount++;
                            
                            // Stop quick refresh after 20 attempts (20 seconds)
                            if (refreshCount >= 20) {
                              clearInterval(quickRefresh);
                            }
                          }, 1000);
                        }
                      }}
                      disabled={!selectedDroplet}
                      dropletContext={selectedDroplet ? {
                        id: selectedDroplet.id,
                        cloudId: selectedDroplet.cloudId,
                        name: selectedDroplet.name,
                        provider: selectedDroplet.provider,
                        powerStatus: selectedDroplet.powerStatus,
                        ip: selectedDroplet.ip,
                        region: selectedDroplet.region
                      } : undefined}
                      userContext={{
                        userId: 'current-user', // Replace with actual user ID
                        sessionId: `chat-${selectedDroplet?.id || 'none'}`
                      }}
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={!message.trim()}
                      className="p-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg transition-all duration-200 hover:scale-105 disabled:hover:scale-100 shadow-sm disabled:shadow-none"
                    >
                      <Send className="text-white" size={16} />
                    </button>
                  </div>
                  <div className="mt-2">
                    <p className="text-xs text-gray-500 dark:text-slate-400">
                      Available: <kbd className="px-1.5 py-0.5 bg-gray-200/80 dark:bg-slate-600/50 rounded text-xs font-mono">reboot</kbd> <kbd className="px-1.5 py-0.5 bg-gray-200/80 dark:bg-slate-600/50 rounded text-xs font-mono">power off</kbd> <kbd className="px-1.5 py-0.5 bg-gray-200/80 dark:bg-slate-600/50 rounded text-xs font-mono">power on</kbd> <kbd className="px-1.5 py-0.5 bg-red-200/80 dark:bg-red-900/50 rounded text-xs font-mono text-red-700 dark:text-red-400">delete</kbd> • 🎤 Voice commands enabled
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center animate-fade-in">
                  <div className="w-14 h-14 bg-gray-100/80 dark:bg-slate-700/50 rounded-xl flex items-center justify-center mx-auto mb-3 border border-gray-200/60 dark:border-slate-600/50">
                    <Send className="text-gray-400" size={20} />
                  </div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">Select a server</h3>
                  <p className="text-sm text-gray-500 dark:text-slate-400">Choose a server to start managing</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

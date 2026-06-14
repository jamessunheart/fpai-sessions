import { X, Server, Network, Clock, Tag, MapPin, Activity, Calendar, Info } from 'lucide-react';
import { Droplet } from '../../../types';
import { Card } from '../../../shared/components';

interface DropletDetailsProps {
  droplet: Droplet;
  onClose: () => void;
}

export default function DropletDetails({ droplet, onClose }: DropletDetailsProps) {
  const formatLastSeen = (timestamp: number | string) => {
    if (!timestamp) return 'Never';
    const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp);
    return date.toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'text-green-600 bg-green-100 dark:bg-green-500/20 dark:text-green-400';
      case 'healthy': return 'text-green-600 bg-green-100 dark:bg-green-500/20 dark:text-green-400';
      case 'down': return 'text-red-600 bg-red-100 dark:bg-red-500/20 dark:text-red-400';
      case 'inactive': return 'text-red-600 bg-red-100 dark:bg-red-500/20 dark:text-red-400';
      default: return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-500/20 dark:text-yellow-400';
    }
  };

  const name = droplet.name || droplet.id || 'Unknown';
  const status = droplet.status || 'unknown';
  const role = droplet.role || droplet.metadata?.role || 'N/A';
  const version = droplet.version || droplet.metadata?.version || 'N/A';
  const env = droplet.env || 'prod';
  const host = droplet.host || droplet.fqdn || 'N/A';
  const lastSeen = droplet.last_heartbeat || droplet.last_seen || 0;
  const health = droplet.health || { available: false };
  const healthStatus = health.available ? health.status : 'unavailable';

  const getStatusBadge = () => {
    switch (healthStatus) {
      case 'active':
        return {
          bg: 'bg-green-100 dark:bg-green-500/20',
          text: 'text-green-700 dark:text-green-300',
          label: 'Active',
          icon: '🟢'
        };
      case 'inactive':
        return {
          bg: 'bg-yellow-100 dark:bg-yellow-500/20',
          text: 'text-yellow-700 dark:text-yellow-300',
          label: 'Inactive',
          icon: '🟡'
        };
      case 'error':
        return {
          bg: 'bg-red-100 dark:bg-red-500/20',
          text: 'text-red-700 dark:text-red-300',
          label: 'Error',
          icon: '🔴'
        };
      default:
        return {
          bg: 'bg-slate-100 dark:bg-slate-500/20',
          text: 'text-slate-700 dark:text-slate-300',
          label: 'Offline',
          icon: '⚪'
        };
    }
  };

  const statusBadge = getStatusBadge();

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-fadeIn" onClick={onClose}>
      <div className="bg-white dark:bg-slate-800 rounded-2xl max-w-5xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-slideUp border border-slate-200 dark:border-slate-700" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="relative bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 p-6 text-white">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-white/20 rounded-lg transition-all hover:rotate-90 duration-300"
          >
            <X size={20} />
          </button>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl shadow-lg">
              <Server size={28} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-2xl font-bold">{name}</h2>
                <span className={`px-3 py-1 ${statusBadge.bg} ${statusBadge.text} rounded-full text-xs font-semibold flex items-center gap-1.5`}>
                  <span>{statusBadge.icon}</span>
                  {statusBadge.label}
                </span>
              </div>
              <p className="text-blue-100 mb-2 text-sm">{host}</p>
              <div className="flex items-center gap-2">
                {version !== 'N/A' && (
                  <span className="px-3 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium">
                    📦 v{version}
                  </span>
                )}
                <span className="px-3 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium uppercase">
                  🌍 {env}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status Banner */}
          <div className={`rounded-xl p-6 border-2 ${
            healthStatus === 'active' ? 'bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30' :
            healthStatus === 'inactive' ? 'bg-yellow-50 dark:bg-yellow-500/10 border-yellow-200 dark:border-yellow-500/30' :
            healthStatus === 'error' ? 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30' :
            'bg-slate-50 dark:bg-slate-500/10 border-slate-200 dark:border-slate-500/30'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${
                  healthStatus === 'active' ? 'bg-green-100 dark:bg-green-500/20' :
                  healthStatus === 'inactive' ? 'bg-yellow-100 dark:bg-yellow-500/20' :
                  healthStatus === 'error' ? 'bg-red-100 dark:bg-red-500/20' :
                  'bg-slate-100 dark:bg-slate-500/20'
                }`}>
                  <Activity className={`${
                    healthStatus === 'active' ? 'text-green-600 dark:text-green-400' :
                    healthStatus === 'inactive' ? 'text-yellow-600 dark:text-yellow-400' :
                    healthStatus === 'error' ? 'text-red-600 dark:text-red-400' :
                    'text-slate-600 dark:text-slate-400'
                  }`} size={24} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400 font-medium">Current Status</p>
                  <p className={`text-2xl font-bold ${
                    healthStatus === 'active' ? 'text-green-700 dark:text-green-300' :
                    healthStatus === 'inactive' ? 'text-yellow-700 dark:text-yellow-300' :
                    healthStatus === 'error' ? 'text-red-700 dark:text-red-300' :
                    'text-slate-700 dark:text-slate-300'
                  }`}>
                    {statusBadge.icon} {statusBadge.label}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-600 dark:text-slate-400">Last Updated</p>
                <p className="text-sm font-mono text-black dark:text-white">
                  {health.updated_at ? new Date(health.updated_at).toLocaleTimeString() : 'N/A'}
                </p>
              </div>
            </div>
          </div>



          {/* Health Details */}
          {health.available && (
            <Card>
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4 flex items-center gap-2">
                <Activity className="text-green-600 dark:text-green-400" size={20} />
                Droplet Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {health.cost_usd !== undefined && (
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Tag className="text-blue-500" size={16} />
                      <p className="text-sm text-slate-600 dark:text-slate-400">Cost</p>
                    </div>
                    <p className="text-xl font-bold text-black dark:text-white">
                      ${health.cost_usd}
                    </p>
                  </div>
                )}
                
                {health.yield_usd !== undefined && (
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="text-green-500" size={16} />
                      <p className="text-sm text-slate-600 dark:text-slate-400">Yield</p>
                    </div>
                    <p className="text-xl font-bold text-black dark:text-white">
                      ${health.yield_usd}
                    </p>
                  </div>
                )}
                
                {health.proof && (
                  <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Server className="text-purple-500" size={16} />
                      <p className="text-sm text-slate-600 dark:text-slate-400">Proof Hash</p>
                    </div>
                    <p className="text-xs font-mono text-black dark:text-white truncate">
                      {health.proof.substring(0, 16)}...
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Network Information */}
          <Card>
            <h3 className="text-lg font-semibold text-black dark:text-white mb-4 flex items-center gap-2">
              <Network className="text-blue-600 dark:text-blue-400" size={20} />
              Network Information
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className="text-blue-500" size={16} />
                  <p className="text-sm text-slate-600 dark:text-slate-400">Droplet ID</p>
                </div>
                <p className="font-mono text-sm text-black dark:text-white break-all">{droplet.id}</p>
              </div>
              
              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Server className="text-purple-500" size={16} />
                  <p className="text-sm text-slate-600 dark:text-slate-400">Host</p>
                </div>
                <p className="font-mono text-sm text-black dark:text-white break-all">{host}</p>
              </div>
            </div>
          </Card>

          {/* Metadata */}
          {droplet.metadata && Object.keys(droplet.metadata).length > 0 && (
            <Card>
              <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Metadata</h3>
              <div className="space-y-2">
                {Object.entries(droplet.metadata).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-black dark:text-slate-400">{key}:</span>
                    <span className="text-black dark:text-white font-medium">{String(value)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Timeline */}
          <Card>
            <h3 className="text-lg font-semibold text-black dark:text-white mb-4 flex items-center gap-2">
              <Calendar className="text-blue-600 dark:text-blue-400" size={20} />
              Timeline
            </h3>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-blue-100 dark:bg-blue-500/20 rounded-lg">
                  <Calendar className="text-blue-600 dark:text-blue-400" size={18} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-black dark:text-white">Registered</p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{formatLastSeen(droplet.registered_at)}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="p-2 bg-purple-100 dark:bg-purple-500/20 rounded-lg">
                  <Clock className="text-purple-600 dark:text-purple-400" size={18} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-black dark:text-white">Last Updated</p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{formatLastSeen(droplet.last_updated)}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="p-2 bg-green-100 dark:bg-green-500/20 rounded-lg">
                  <Activity className="text-green-600 dark:text-green-400" size={18} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-black dark:text-white">Last Heartbeat</p>
                  <p className="text-sm text-slate-600 dark:text-slate-400">{formatLastSeen(lastSeen)}</p>
                  {lastSeen && (() => {
                    const now = Math.floor(Date.now() / 1000);
                    const diff = now - (typeof lastSeen === 'number' ? lastSeen : 0);
                    const minutes = Math.floor(diff / 60);
                    const hours = Math.floor(diff / 3600);
                    const days = Math.floor(diff / 86400);
                    
                    let timeAgo = '';
                    if (diff < 60) timeAgo = 'Just now';
                    else if (diff < 3600) timeAgo = `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
                    else if (diff < 86400) timeAgo = `${hours} hour${hours !== 1 ? 's' : ''} ago`;
                    else timeAgo = `${days} day${days !== 1 ? 's' : ''} ago`;
                    
                    const isRecent = diff < 300;
                    return (
                      <span className={`inline-flex items-center gap-1 mt-1 text-xs font-medium ${
                        isRecent ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400'
                      }`}>
                        <span className={`w-2 h-2 rounded-full ${
                          isRecent ? 'bg-green-500 animate-pulse' : 'bg-orange-500'
                        }`}></span>
                        {timeAgo}
                      </span>
                    );
                  })()}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
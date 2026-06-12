import React from 'react';
import Card from '../../../shared/components/Card';
import { Droplet } from '../../../types';
import { STATUS_COLORS } from '../../../shared/utils/constants';
import { Server, Clock, MapPin, Tag } from 'lucide-react';

interface DropletCardProps {
  droplet: Droplet;
  health?: any;
  onClick?: () => void;
}

function DropletCard({ droplet, health, onClick }: DropletCardProps) {
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return STATUS_COLORS.OK;
      case 'healthy': return STATUS_COLORS.OK;
      case 'down': return STATUS_COLORS.ERROR;
      case 'inactive': return STATUS_COLORS.ERROR;
      default: return STATUS_COLORS.WARNING;
    }
  };

  const getTimeAgo = (timestamp: number) => {
    if (!timestamp) return 'Never';
    const now = Math.floor(Date.now() / 1000);
    const diff = now - timestamp;
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const name = droplet.name || droplet.id || 'Unknown';
  const status = droplet.status || 'unknown';
  const role = droplet.role || droplet.metadata?.role || 'N/A';
  const host = droplet.host || 'N/A';
  const lastHeartbeat = droplet.last_heartbeat || 0;
  const version = droplet.version || droplet.metadata?.version || 'N/A';
  const env = droplet.env || 'prod';
  const healthData = health || { available: false };
  const healthStatus = healthData.available ? healthData.status : 'unavailable';

  const isOnline = () => {
    if (!lastHeartbeat) return false;
    const now = Math.floor(Date.now() / 1000);
    return (now - lastHeartbeat) < 300; // 5 minutes
  };

  return (
    <Card 
      className="bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-800/50 cursor-pointer transform transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl border-2 border-transparent hover:border-blue-500/50 hover:-translate-y-1" 
      hover
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className={`p-2 rounded-lg ${
            healthStatus === 'active' ? 'bg-green-100 dark:bg-green-500/20' : 
            healthStatus === 'inactive' ? 'bg-yellow-100 dark:bg-yellow-500/20' :
            healthStatus === 'error' ? 'bg-red-100 dark:bg-red-500/20' :
            'bg-slate-100 dark:bg-slate-700'
          }`}>
            <Server className={
              healthStatus === 'active' ? 'text-green-600 dark:text-green-400' : 
              healthStatus === 'inactive' ? 'text-yellow-600 dark:text-yellow-400' :
              healthStatus === 'error' ? 'text-red-600 dark:text-red-400' :
              'text-slate-400'
            } size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-black dark:text-white truncate">{name}</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{droplet.id}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className={`w-3 h-3 rounded-full ${
            healthStatus === 'active' ? 'bg-green-500 animate-pulse shadow-lg shadow-green-500/50' :
            healthStatus === 'inactive' ? 'bg-yellow-500 shadow-lg shadow-yellow-500/30' :
            healthStatus === 'error' ? 'bg-red-500 animate-pulse shadow-lg shadow-red-500/50' :
            'bg-slate-400'
          }`}></div>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-2 text-sm">
        {role !== 'N/A' && (
          <div className="flex items-center gap-2 text-black dark:text-slate-300">
            <Tag size={14} className="text-blue-500" />
            <span className="font-medium">Role:</span>
            <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded text-xs">
              {role}
            </span>
          </div>
        )}
        
        <div className="flex items-center gap-2 text-black dark:text-slate-300">
          <MapPin size={14} className="text-purple-500" />
          <span className="font-medium">Host:</span>
          <span className="truncate text-slate-600 dark:text-slate-400">{host}</span>
        </div>

        {version !== 'N/A' && (
          <div className="flex items-center gap-2 text-black dark:text-slate-300">
            <Tag size={14} className="text-green-500" />
            <span className="font-medium">Version:</span>
            <span className="text-slate-600 dark:text-slate-400">{version}</span>
          </div>
        )}

        {healthData.available && healthData.name && (
          <div className="flex items-center gap-2 text-black dark:text-slate-300">
            <Server size={14} className="text-indigo-500" />
            <span className="font-medium">Name:</span>
            <span className="text-slate-600 dark:text-slate-400">{healthData.name}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
            <Clock size={12} />
            <span>{getTimeAgo(lastHeartbeat)}</span>
          </div>
          <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded">
            {env}
          </span>
        </div>
      </div>
    </Card>
  );
}

export default React.memo(DropletCard);
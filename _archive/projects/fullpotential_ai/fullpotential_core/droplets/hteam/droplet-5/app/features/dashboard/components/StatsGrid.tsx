import StatsCard from '../../../components/StatsCard';
import { DashboardStats } from '../../../types';
import { Zap, Clock, CheckCircle, Activity, Server, Cpu, HardDrive } from 'lucide-react';

interface StatsGridProps {
  stats: DashboardStats;
  loading: boolean;
}

export default function StatsGrid({ stats, loading }: StatsGridProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Sprints"
          value={stats.totalSprints}
          icon={Zap}
          loading={loading}
        />
        <StatsCard
          title="Active Sprints"
          value={stats.activeSprints}
          change={`${stats.activeSprints} running`}
          changeType="positive"
          icon={Clock}
          loading={loading}
        />
        <StatsCard
          title="Completed"
          value={stats.completedSprints}
          change={`${((stats.completedSprints / stats.totalSprints) * 100 || 0).toFixed(1)}% done`}
          changeType="positive"
          icon={CheckCircle}
          loading={loading}
        />
        <StatsCard
          title="System Uptime"
          value={`${stats.uptime.toFixed(1)}%`}
          change={`${stats.activeDroplets}/${stats.totalDroplets} online`}
          changeType={stats.uptime > 90 ? 'positive' : 'negative'}
          icon={Activity}
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatsCard
          title="Total Droplets"
          value={stats.totalDroplets}
          icon={Server}
          loading={loading}
        />
        <StatsCard
          title="Average CPU"
          value={`${stats.avgCpu.toFixed(1)}%`}
          icon={Cpu}
          loading={loading}
        />
        <StatsCard
          title="Average RAM"
          value={`${stats.avgRam.toFixed(1)}%`}
          icon={HardDrive}
          loading={loading}
        />
      </div>
    </div>
  );
}
import { useWebhooks } from '../hooks/useWebhooks';
import { Shield, Activity, Zap } from 'lucide-react';

export default function NotificationDemo() {
  const { triggerSprintCompletion, triggerInfrastructureAlert } = useWebhooks();

  return (
    <div className="fixed bottom-4 right-4 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-gray-200 dark:border-slate-700 p-4 z-50">
      <h4 className="font-semibold text-black dark:text-white mb-3">Test Notifications</h4>
      <div className="space-y-2">
        <button
          onClick={() => triggerSprintCompletion('SPRINT-001', 'Frontend Dashboard')}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/30 transition-colors"
        >
          <Shield size={16} />
          Sprint Completed
        </button>
        
        <button
          onClick={() => triggerInfrastructureAlert('drop1', 'high_cpu')}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 rounded-lg hover:bg-yellow-200 dark:hover:bg-yellow-900/30 transition-colors"
        >
          <Activity size={16} />
          High CPU Alert
        </button>
        
        <button
          onClick={() => triggerInfrastructureAlert('drop2', 'offline')}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/30 transition-colors"
        >
          <Zap size={16} />
          Droplet Offline
        </button>
      </div>
    </div>
  );
}
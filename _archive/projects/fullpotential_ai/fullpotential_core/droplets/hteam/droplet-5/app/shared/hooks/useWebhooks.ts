import { useNotifications } from '../contexts/NotificationContext';
import { api } from '../../lib/api';

export function useWebhooks() {
  const { addNotification } = useNotifications();

  const sendProofNotification = async (data: {
    proof_id: string;
    sprint_id?: string;
    status?: string;
  }) => {
    try {
      await api.sendProofWebhook(data);
      
      addNotification({
        type: 'proof',
        title: 'Proof Submitted',
        message: `Proof ${data.proof_id} has been submitted successfully`,
        data
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Proof Submission Failed',
        message: `Failed to submit proof ${data.proof_id}`,
        data
      });
    }
  };

  const sendHeartbeatNotification = async (data: {
    cell_id: string;
    status?: string;
    cpu?: number;
    memory?: number;
  }) => {
    try {
      await api.sendHeartbeatWebhook(data);
      
      const isHealthy = data.status === 'healthy' || (!data.status && (data.cpu || 0) < 80 && (data.memory || 0) < 80);
      
      addNotification({
        type: isHealthy ? 'heartbeat' : 'warning',
        title: isHealthy ? 'System Healthy' : 'System Alert',
        message: isHealthy 
          ? `Droplet ${data.cell_id} is running normally`
          : `Droplet ${data.cell_id} needs attention - High resource usage`,
        data
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Heartbeat Failed',
        message: `Failed to send heartbeat for ${data.cell_id}`,
        data
      });
    }
  };

  const triggerSprintCompletion = async (sprintId: string, sprintName: string) => {
    await sendProofNotification({
      proof_id: `PROOF-${sprintId}`,
      sprint_id: sprintId,
      status: 'completed'
    });
  };

  const triggerInfrastructureAlert = async (dropletId: string, alertType: 'high_cpu' | 'high_memory' | 'offline') => {
    const alertData = {
      high_cpu: { cpu: 95, status: 'warning' },
      high_memory: { memory: 90, status: 'warning' },
      offline: { status: 'offline' }
    };

    await sendHeartbeatNotification({
      cell_id: dropletId,
      ...alertData[alertType]
    });
  };

  return {
    sendProofNotification,
    sendHeartbeatNotification,
    triggerSprintCompletion,
    triggerInfrastructureAlert
  };
}
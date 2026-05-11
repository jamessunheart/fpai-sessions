import { heartbeatService } from '../../lib/heartbeat';

export async function GET() {
  // Manually trigger a heartbeat
  await heartbeatService.sendHeartbeat();
  
  return Response.json({ 
    message: 'Heartbeat sent to Orchestrator',
    timestamp: new Date().toISOString()
  });
}

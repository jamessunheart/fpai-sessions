import { heartbeatService } from './heartbeat';
import { registryClient } from './registry-client';

let initialized = false;

// Initialize UDC services on application startup
export function initializeUDCServices() {
  if (typeof window === 'undefined' && !initialized) {
    initialized = true;
    console.log('Initializing UDC services...');
    heartbeatService.start();
    registryClient.start();
    
    // Graceful shutdown handling
    process.on('SIGTERM', () => {
      console.log('SIGTERM received, stopping UDC services...');
      heartbeatService.stop();
      registryClient.stop();
      process.exit(0);
    });
    
    process.on('SIGINT', () => {
      console.log('SIGINT received, stopping UDC services...');
      heartbeatService.stop();
      registryClient.stop();
      process.exit(0);
    });
  }
}

// Auto-initialize when module is imported
initializeUDCServices();
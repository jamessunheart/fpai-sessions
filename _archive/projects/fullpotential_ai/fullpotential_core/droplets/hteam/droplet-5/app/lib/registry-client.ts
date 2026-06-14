const REGISTRY_BASE = process.env.REGISTRY_URL || 'https://drop18.fullpotential.ai';
const REGISTRY_KEY = process.env.REGISTRY_API_KEY || '';
const DROPLET_ID = process.env.DROPLET_ID || 'drop5.fullpotential.ai';

class RegistryClient {
  private token: string | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  async getToken(): Promise<string> {
    try {
      const response = await fetch(`${REGISTRY_BASE}/auth/token?droplet_id=${DROPLET_ID}`, {
        method: 'POST',
        headers: {
          'X-Registry-Key': REGISTRY_KEY,
        },
      });
      
      if (!response.ok) {
        console.error(`❌ Token fetch failed: ${response.status}`);
        return '';
      }

      const data = await response.json();
      this.token = data.token;
      console.log('✅ Token fetched, using immediately');
      return this.token;
    } catch (error) {
      console.error('❌ Token fetch error:', error);
      return '';
    }
  }

  async register(): Promise<void> {
    if (!this.token) {
      const token = await this.getToken();
      if (!token) return;
    }

    try {
      // Get real IP address
      let realIp = '0.0.0.0';
      try {
        const ipResponse = await fetch('https://api.ipify.org?format=json');
        if (ipResponse.ok) {
          const ipData = await ipResponse.json();
          realIp = ipData.ip;
        }
      } catch (e) {
        console.log('⚠️ Could not fetch real IP, using 0.0.0.0');
      }

      const payload = {
        id: DROPLET_ID,
        droplet_id: DROPLET_ID,
        host: DROPLET_ID,
        ip: realIp,
        name: 'Full Potential Dashboard',
        role: 'dashboard',
        env: 'prod',
        version: '1.0.0',
        steward: 'Haythem',
        endpoint: `https://${DROPLET_ID}`,
        capabilities: ['dashboard', 'monitoring', 'visualization', 'udc-v1.0'],
        status: 'active',
        metadata: {
          version: '1.0.0',
          name: 'Full Potential Dashboard',
          steward: 'Haythem',
          udc_version: '1.0',
        },
      };
      
      console.log('📝 Registering with payload:', JSON.stringify(payload, null, 2));
      
      const response = await fetch(`${REGISTRY_BASE}/registry/register`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Registry-Key': REGISTRY_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      console.log(`📝 Register response status: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Registered with Registry v2:', data);
      } else {
        const errorText = await response.text();
        console.error(`❌ Registration failed: ${response.status}`);
        console.error(`❌ Error details: ${errorText}`);
      }
    } catch (error) {
      console.error('❌ Registration error:', error);
    }
  }

  async sendHeartbeat(): Promise<void> {
    try {
      await this.getToken();
      
      const { getSystemState } = await import('./udc');
      const state = getSystemState();
      
      const response = await fetch(`${REGISTRY_BASE}/registry/heartbeat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Registry-Key': REGISTRY_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: DROPLET_ID,
          droplet_id: DROPLET_ID,
          host: DROPLET_ID,
          status: 'active',
          load: state.cpu_percent / 100,
          metadata: {
            cpu_percent: state.cpu_percent,
            memory_mb: state.memory_mb,
            requests_per_minute: state.requests_per_minute || 0,
            errors_last_hour: state.errors_last_hour || 0,
            uptime_seconds: state.uptime_seconds,
          },
        }),
      });
      
      if (response.ok) {
        console.log('💓 Heartbeat sent to Registry');
      } else {
        const errorText = await response.text();
        console.error(`❌ Heartbeat failed: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      console.error('❌ Heartbeat error:', error);
    }
  }

  start(): void {
    console.log('🚀 Starting Registry v2 integration...');
    
    // Register on startup
    this.register();

    // Send heartbeat every 30 seconds
    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeat();
    }, 30000);
  }

  stop(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
      console.log('🛑 Stopped Registry v2 heartbeats');
    }
  }
}

export const registryClient = new RegistryClient();

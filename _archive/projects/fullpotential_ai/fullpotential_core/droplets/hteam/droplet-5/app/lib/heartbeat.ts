import { UDC_CONFIG, getSystemState } from './udc';
import jwt from 'jsonwebtoken';
import fs from 'fs';
import path from 'path';

class HeartbeatService {
  private intervalId: NodeJS.Timeout | null = null;
  private orchestratorUrl: string;
  private orchestratorJwt: string;
  private registered: boolean = false;
  
  constructor() {
    this.orchestratorUrl = process.env.ORCHESTRATOR_URL || 'https://drop10.fullpotential.ai';
    this.orchestratorJwt = this.generateToken();
  }

  private generateToken(): string {
    try {
      const privateKeyPath = path.join(process.cwd(), 'private_key.pem');
      const privateKey = fs.readFileSync(privateKeyPath, 'utf8');
      
      const now = Math.floor(Date.now() / 1000);
      const payload = {
        droplet_id: 5,
        steward: "Haythem",
        permissions: ["read", "write"],
        iat: now,
        exp: now + (23 * 60 * 60) // 23 hours to refresh before expiry
      };
      
      const token = jwt.sign(payload, privateKey, { algorithm: 'RS256' });
      const expiryDate = new Date((now + (23 * 60 * 60)) * 1000).toISOString();
      console.log(`🔑 Generated fresh JWT token (expires: ${expiryDate})`);
      return token;
    } catch (error) {
      console.error('❌ Failed to generate token:', error);
      return process.env.ORCHESTRATOR_JWT || '';
    }
  }

  async sendHeartbeat() {
    try {
      if (!this.orchestratorJwt) {
        console.log('⏳ No ORCHESTRATOR_JWT, skipping heartbeat');
        return;
      }
      const state = getSystemState();
      const now = new Date();
      
      const udcMessage = {
        message_type: 'command',
        payload: {
          metrics: {
            cpu_percent: state.cpu_percent,
            memory_mb: state.memory_mb,
            requests_per_minute: state.requests_per_minute || 0
          },
          status: 'active'
        },
        source: 'droplet-5',
        target: 'droplet-10',
        timestamp: now.toISOString(),
        trace_id: crypto.randomUUID(),
        udc_version: '1.0'
      };

      console.log(`💓 Sending heartbeat to Orchestrator: ${this.orchestratorUrl}/droplets/5/heartbeat`);

      const response = await fetch(`${this.orchestratorUrl}/droplets/5/heartbeat`, {
        method: 'POST',
        headers: { 
          'accept': 'application/json',
          'Authorization': `Bearer ${this.orchestratorJwt}`,
          'Content-Type': 'application/json' 
        },
        body: JSON.stringify(udcMessage)
      });
      
      console.log(`💓 Orchestrator response status: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Heartbeat sent to Orchestrator:', data);
      } else {
        const errorText = await response.text();
        console.error(`❌ Heartbeat failed: ${response.status} - ${errorText}`);
        
        if (response.status === 401 && errorText.includes('expired')) {
          console.log('🔄 Token expired, regenerating...');
          this.orchestratorJwt = this.generateToken();
        }
      }
    } catch (error) {
      console.error('❌ Orchestrator connection error:', error);
    }
  }

  async registerWithOrchestrator() {
    try {
      if (!this.orchestratorJwt) {
        console.log('⚠️ No ORCHESTRATOR_JWT in .env');
        return;
      }
      
      const payload = {
        message_type: 'command',
        payload: {
          droplet_id: 5,
          name: 'Full Potential Dashboard',
          endpoint: 'https://drop5.fullpotential.ai',
          steward: 'Haythem',
          capabilities: ['monitoring', 'dashboard', 'visualization']
        },
        source: 'droplet-5',
        target: 'droplet-10',
        timestamp: new Date().toISOString(),
        trace_id: crypto.randomUUID(),
        udc_version: '1.0'
      };

      console.log('📝 Registering with Orchestrator...');
      const response = await fetch(`${this.orchestratorUrl}/droplets/register`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.orchestratorJwt}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      console.log(`📝 Registration response: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Registered with Orchestrator:', data);
        this.registered = true;
      } else {
        const errorText = await response.text();
        console.error(`❌ Registration failed: ${response.status}`);
        console.error(`❌ Error: ${errorText}`);
        
        if (response.status === 401) {
          console.log('🔄 Token invalid during registration, generating new token...');
          this.orchestratorJwt = this.generateToken();
          console.log('♻️ Retrying registration with new token...');
          await this.registerWithOrchestrator();
        }
      }
    } catch (error) {
      console.error('❌ Orchestrator registration error:', error);
    }
  }

  start() {
    this.registerWithOrchestrator();
    
    // Send heartbeat every 60s
    this.intervalId = setInterval(() => {
      this.sendHeartbeat();
    }, 60000);
    
    // Refresh token every 22 hours (before 23h expiry)
    setInterval(() => {
      console.log('⏰ Scheduled token refresh (22h interval)');
      this.orchestratorJwt = this.generateToken();
    }, 22 * 60 * 60 * 1000);
    
    this.sendHeartbeat();
    
    console.log('🫀 Heartbeat service started - sending to Orchestrator every 60s');
    console.log('🔄 Token auto-refresh enabled (every 22 hours)');
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}

export const heartbeatService = new HeartbeatService();

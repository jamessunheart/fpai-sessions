import { NextRequest } from 'next/server';
import jwt from 'jsonwebtoken';
import os from 'os';
import fs from 'fs';
import path from 'path';

// UDC Configuration
const UDC_CONFIG = {
  droplet: {
    id: 5,
    name: "Full Potential Dashboard",
    steward: "Haythem",
    version: "1.0.0"
  }
};

// System metrics tracking
let systemMetrics = {
  startTime: Date.now(),
  requestCount: 0,
  errorCount: 0,
  lastRestart: new Date().toISOString()
};

// Load public key for RS256 verification
let publicKey: string;
try {
  publicKey = fs.readFileSync(path.join(process.cwd(), 'public_key.pem'), 'utf8');
} catch (error) {
  console.warn('⚠️ public_key.pem not found');
  publicKey = '';
}

export function verifyJWT(token: string): any {
  try {
    if (publicKey) {
      return jwt.verify(token, publicKey, {
        algorithms: ['RS256']
      });
    } else {
      const decoded = jwt.decode(token);
      if (!decoded) throw new Error('Invalid JWT token');
      return decoded;
    }
  } catch (error) {
    throw new Error('Invalid JWT token');
  }
}

// Authentication middleware
export function requireAuth(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    throw new Error('Missing or invalid authorization header');
  }
  
  const token = authHeader.substring(7);
  return verifyJWT(token);
}

// Get real CPU usage (average load)
function getCPUUsage(): number {
  const loadAvg = os.loadavg()[0]; // 1-minute load average
  const cpuCount = os.cpus().length;
  const usage = (loadAvg / cpuCount) * 100;
  return Math.round(Math.max(0, Math.min(100, usage)));
}

// Get system resource usage
export function getSystemState() {
  const uptime = Math.floor((Date.now() - systemMetrics.startTime) / 1000);
  const memoryUsage = process.memoryUsage();
  
  return {
    cpu_percent: getCPUUsage(), // REAL CPU usage
    memory_mb: Math.round(memoryUsage.heapUsed / 1024 / 1024),
    uptime_seconds: uptime,
    requests_total: systemMetrics.requestCount,
    requests_per_minute: Math.round(systemMetrics.requestCount / (uptime / 60)),
    errors_last_hour: systemMetrics.errorCount,
    last_restart: systemMetrics.lastRestart
  };
}

// Increment request counter
export function incrementRequestCount() {
  systemMetrics.requestCount++;
}

// Increment error counter
export function incrementErrorCount() {
  systemMetrics.errorCount++;
}

// Standard UDC response format
export function createUDCResponse(data: any, status: 'success' | 'error' = 'success') {
  return {
    status,
    data,
    timestamp: new Date().toISOString()
  };
}

// Standard UDC error response
export function createUDCError(code: string, message: string, details: any = {}) {
  return {
    status: 'error',
    error: {
      code,
      message,
      details
    },
    timestamp: new Date().toISOString()
  };
}

export { UDC_CONFIG };
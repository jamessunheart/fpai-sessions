// Discover Orchestrator endpoints
const BASE_URL = 'https://drop10.fullpotential.ai';

const possibleEndpoints = [
  '/health',
  '/capabilities',
  '/state',
  '/dependencies',
  '/message',
  '/send',
  '/version',
  '/heartbeat',
  '/heartbeats',
  '/register',
  '/droplets',
  '/status',
  '/metrics',
  '/report'
];

async function discoverEndpoints() {
  console.log('🔍 Discovering Orchestrator endpoints...\n');

  for (const endpoint of possibleEndpoints) {
    try {
      const response = await fetch(`${BASE_URL}${endpoint}`);
      if (response.status !== 404) {
        console.log(`✅ ${endpoint} - Status: ${response.status}`);
        try {
          const data = await response.json();
          console.log(`   Response:`, JSON.stringify(data, null, 2));
        } catch {
          const text = await response.text();
          console.log(`   Response: ${text}`);
        }
        console.log('');
      }
    } catch (error) {
      // Skip errors
    }
  }
}

discoverEndpoints();

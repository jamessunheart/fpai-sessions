// Test script for Orchestrator heartbeat with Droplet #1 JWT token
const REGISTRY_URL = 'https://drop1.fullpotential.ai';
const REGISTRY_KEY = 'regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da';
const ORCHESTRATOR_URL = 'https://drop10.fullpotential.ai';

async function getJWTToken() {
  console.log('🔑 Step 1: Getting JWT token from Registry (Droplet #1)...');
  console.log(`🔑 URL: ${REGISTRY_URL}/jwt/issue`);
  
  const response = await fetch(`${REGISTRY_URL}/jwt/issue`, {
    method: 'POST',
    headers: {
      'X-Registry-Key': REGISTRY_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      droplet_id: '5',
      expires_in: 3600
    })
  });

  console.log(`🔑 Response status: ${response.status}`);
  
  if (response.ok) {
    const data = await response.json();
    console.log('✅ Got JWT token!');
    console.log(`✅ Token: ${data.token.substring(0, 50)}...`);
    console.log(`✅ Expires at: ${data.expires_at}`);
    console.log(`✅ Droplet ID: ${data.droplet_id}`);
    return data.token;
  } else {
    const error = await response.text();
    console.error('❌ Failed to get token:', error);
    return null;
  }
}

async function sendHeartbeat(token) {
  console.log('\n💓 Step 2: Sending heartbeat to Orchestrator (Droplet #10)...');
  console.log(`💓 URL: ${ORCHESTRATOR_URL}/droplets/5/heartbeat`);
  
  const payload = {
    message_type: 'command',
    payload: {
      metrics: {
        cpu_percent: 15.5,
        memory_mb: 512,
        requests_per_minute: 50
      },
      status: 'active'
    },
    source: 'droplet-5',
    target: 'droplet-10',
    timestamp: new Date().toISOString(),
    trace_id: crypto.randomUUID(),
    udc_version: '1.0'
  };

  console.log('💓 Payload:', JSON.stringify(payload, null, 2));

  const response = await fetch(`${ORCHESTRATOR_URL}/droplets/5/heartbeat`, {
    method: 'POST',
    headers: {
      'accept': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  console.log(`💓 Response status: ${response.status}`);

  if (response.ok) {
    const data = await response.json();
    console.log('✅ Heartbeat successful!');
    console.log('✅ Response:', JSON.stringify(data, null, 2));
  } else {
    const error = await response.text();
    console.error('❌ Heartbeat failed!');
    console.error('❌ Error:', error);
  }
}

async function test() {
  console.log('🚀 Testing Orchestrator Heartbeat with Droplet #1 JWT\n');
  console.log('=' .repeat(60));
  
  const token = await getJWTToken();
  
  if (token) {
    await sendHeartbeat(token);
  } else {
    console.error('❌ Cannot test heartbeat without token');
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('🏁 Test complete!');
}

test().catch(console.error);

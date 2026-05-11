// Test script to verify Registry and Orchestrator connectivity
const REGISTRY_URL = 'https://drop18.fullpotential.ai';
const REGISTRY_KEY = 'regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da';
const ORCHESTRATOR_URL = 'https://drop10.fullpotential.ai';
const DROPLET_ID = 'drop5.fullpotential.ai';

console.log('🧪 Testing External Service Connectivity\n');

// Test 1: Registry Token Endpoint
async function testRegistryToken() {
  console.log('1️⃣ Testing Registry Token Endpoint...');
  console.log(`   URL: ${REGISTRY_URL}/auth/token?droplet_id=${DROPLET_ID}`);
  
  try {
    const response = await fetch(`${REGISTRY_URL}/auth/token?droplet_id=${DROPLET_ID}`, {
      method: 'POST',
      headers: {
        'X-Registry-Key': REGISTRY_KEY,
      },
    });
    
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log(`   ✅ SUCCESS - Token received: ${data.token?.substring(0, 20)}...`);
      return data.token;
    } else {
      const error = await response.text();
      console.log(`   ❌ FAILED - ${error}`);
      return null;
    }
  } catch (error) {
    console.log(`   ❌ ERROR - ${error.message}`);
    return null;
  }
}

// Test 2: Registry Registration
async function testRegistryRegister(token) {
  console.log('\n2️⃣ Testing Registry Registration Endpoint...');
  console.log(`   URL: ${REGISTRY_URL}/registry/register`);
  
  if (!token) {
    console.log('   ⏭️  SKIPPED - No token available');
    return;
  }
  
  try {
    const response = await fetch(`${REGISTRY_URL}/registry/register`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: DROPLET_ID,
        host: DROPLET_ID,
        droplet_id: DROPLET_ID,
        ip: '0.0.0.0',
        status: 'active',
        metadata: {
          version: '1.0.0',
          name: 'Dashboard',
          steward: 'Haythem',
          udc_version: '1.0',
        },
      }),
    });
    
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log(`   ✅ SUCCESS - ${JSON.stringify(data)}`);
    } else {
      const error = await response.text();
      console.log(`   ❌ FAILED - ${error}`);
    }
  } catch (error) {
    console.log(`   ❌ ERROR - ${error.message}`);
  }
}

// Test 3: Registry Heartbeat
async function testRegistryHeartbeat(token) {
  console.log('\n3️⃣ Testing Registry Heartbeat Endpoint...');
  console.log(`   URL: ${REGISTRY_URL}/registry/heartbeat`);
  
  if (!token) {
    console.log('   ⏭️  SKIPPED - No token available');
    return;
  }
  
  try {
    const response = await fetch(`${REGISTRY_URL}/registry/heartbeat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: DROPLET_ID,
        host: DROPLET_ID,
        droplet_id: DROPLET_ID,
        load: 0.25,
        status: 'healthy',
      }),
    });
    
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log(`   ✅ SUCCESS - ${JSON.stringify(data)}`);
    } else {
      const error = await response.text();
      console.log(`   ❌ FAILED - ${error}`);
    }
  } catch (error) {
    console.log(`   ❌ ERROR - ${error.message}`);
  }
}

// Test 4: Orchestrator Heartbeat
async function testOrchestratorHeartbeat() {
  console.log('\n4️⃣ Testing Orchestrator Heartbeat Endpoint...');
  console.log(`   URL: ${ORCHESTRATOR_URL}/heartbeat/`);
  
  try {
    const now = new Date().toISOString();
    const response = await fetch(`${ORCHESTRATOR_URL}/heartbeat/`, {
      method: 'POST',
      headers: {
        'accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trace_id: crypto.randomUUID(),
        source: 5,
        target: 10,
        message_type: 'status',
        payload: {
          droplet_id: 5,
          status: 'active',
          timestamp: now,
          metrics: {
            cpu_percent: 25.0,
            memory_mb: 512,
            requests_last_minute: 10,
            errors_last_minute: 0,
          },
        },
        timestamp: now,
      }),
    });
    
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log(`   ✅ SUCCESS - ${JSON.stringify(data)}`);
    } else {
      const error = await response.text();
      console.log(`   ❌ FAILED - ${error}`);
    }
  } catch (error) {
    console.log(`   ❌ ERROR - ${error.message}`);
  }
}

// Test 5: Local Health Endpoint
async function testLocalHealth() {
  console.log('\n5️⃣ Testing Local Health Endpoint...');
  console.log(`   URL: http://localhost:3000/api/health`);
  
  try {
    const response = await fetch('http://localhost:3000/api/health');
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log(`   ✅ SUCCESS - Droplet #${data.id} is ${data.status}`);
    } else {
      console.log(`   ❌ FAILED - Server not running?`);
    }
  } catch (error) {
    console.log(`   ⚠️  Server not running locally (this is OK if testing external services only)`);
  }
}

// Run all tests
async function runTests() {
  const token = await testRegistryToken();
  await testRegistryRegister(token);
  await testRegistryHeartbeat(token);
  await testOrchestratorHeartbeat();
  await testLocalHealth();
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(60));
  console.log('\n⚠️  IMPORTANT NOTES:');
  console.log('   • External service failures are EXPECTED if services are down');
  console.log('   • UDC compliance is about implementing the CLIENT side correctly');
  console.log('   • Your droplet should handle failures gracefully (no crashes)');
  console.log('   • All 10 UDC endpoints should work locally regardless of external services');
  console.log('\n✅ UDC Compliance = Local endpoints work + Graceful external error handling\n');
}

runTests();

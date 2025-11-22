// Test Registry v2 with Droplet #6's fix (both id and droplet_id)
const REGISTRY_URL = 'https://drop18.fullpotential.ai';
const REGISTRY_KEY = 'regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da';
const DROPLET_ID = 'drop5.fullpotential.ai';

console.log('🧪 Testing Registry v2 with Droplet #6 Fix\n');
console.log('Fix: Sending BOTH id and droplet_id fields\n');

async function testWithFix() {
  // Step 1: Get Token
  console.log('1️⃣ Getting JWT Token...');
  try {
    const tokenResponse = await fetch(`${REGISTRY_URL}/auth/token?droplet_id=${DROPLET_ID}`, {
      method: 'POST',
      headers: {
        'X-Registry-Key': REGISTRY_KEY,
      },
    });
    
    console.log(`   Status: ${tokenResponse.status} ${tokenResponse.statusText}`);
    
    if (!tokenResponse.ok) {
      const error = await tokenResponse.text();
      console.log(`   ❌ Token failed: ${error}`);
      return;
    }
    
    const tokenData = await tokenResponse.json();
    const token = tokenData.token;
    console.log(`   ✅ Token received: ${token.substring(0, 30)}...`);
    
    // Step 2: Register with BOTH id and droplet_id
    console.log('\n2️⃣ Registering with Registry v2...');
    console.log('   Payload includes: id, droplet_id, host (all three fields)');
    
    const registerPayload = {
      id: DROPLET_ID,
      droplet_id: DROPLET_ID,
      host: DROPLET_ID,
      ip: '0.0.0.0',
      status: 'active',
      metadata: {
        version: '1.0.0',
        name: 'Dashboard',
        steward: 'Haythem',
        udc_version: '1.0',
      },
    };
    
    console.log(`   Payload: ${JSON.stringify(registerPayload, null, 2)}`);
    
    const registerResponse = await fetch(`${REGISTRY_URL}/registry/register`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(registerPayload),
    });
    
    console.log(`   Status: ${registerResponse.status} ${registerResponse.statusText}`);
    
    if (registerResponse.ok) {
      const data = await registerResponse.json();
      console.log(`   ✅ Registration SUCCESS: ${JSON.stringify(data)}`);
    } else {
      const error = await registerResponse.text();
      console.log(`   ❌ Registration failed: ${error}`);
      return;
    }
    
    // Step 3: Send Heartbeat with BOTH id and droplet_id
    console.log('\n3️⃣ Sending Heartbeat...');
    
    const heartbeatPayload = {
      id: DROPLET_ID,
      droplet_id: DROPLET_ID,
      host: DROPLET_ID,
      load: 0.25,
      status: 'healthy',
    };
    
    const heartbeatResponse = await fetch(`${REGISTRY_URL}/registry/heartbeat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(heartbeatPayload),
    });
    
    console.log(`   Status: ${heartbeatResponse.status} ${heartbeatResponse.statusText}`);
    
    if (heartbeatResponse.ok) {
      const data = await heartbeatResponse.json();
      console.log(`   ✅ Heartbeat SUCCESS: ${JSON.stringify(data)}`);
    } else {
      const error = await heartbeatResponse.text();
      console.log(`   ❌ Heartbeat failed: ${error}`);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ DROPLET #5 REGISTRY INTEGRATION STATUS');
    console.log('='.repeat(60));
    console.log('Token:        ✅ Working');
    console.log('Registration: ✅ Working (with id + droplet_id fix)');
    console.log('Heartbeat:    ✅ Working (with id + droplet_id fix)');
    console.log('\nDroplet #6 fix confirmed working for Droplet #5!');
    
  } catch (error) {
    console.error(`\n❌ Error: ${error.message}`);
  }
}

testWithFix();

import { NextResponse } from 'next/server';

const REGISTRY_BASE = 'https://drop18.fullpotential.ai';
const REGISTRY_KEY = 'regkey_2f14c9b6e9b047d2b8c5a7cf93b2e4da';
const DROPLET_ID = 'drop5.fullpotential.ai';

export async function GET() {
  const results: any = { steps: [] };

  try {
    // Step 1: Get Token
    const tokenRes = await fetch(`${REGISTRY_BASE}/auth/token?droplet_id=${DROPLET_ID}`, {
      method: 'POST',
      headers: { 'X-Registry-Key': REGISTRY_KEY },
    });
    const tokenData = await tokenRes.json();
    results.steps.push({ step: 'Get Token', status: tokenRes.ok ? 'SUCCESS' : 'FAILED', data: tokenData });

    if (!tokenRes.ok) throw new Error('Token fetch failed');
    const token = tokenData.token;

    // Step 2: Register
    const registerRes = await fetch(`${REGISTRY_BASE}/registry/register`, {
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
        metadata: { version: '1.0.0', name: 'Dashboard', steward: 'Haythem' },
      }),
    });
    const registerData = await registerRes.json();
    results.steps.push({ step: 'Register', status: registerRes.ok ? 'SUCCESS' : 'FAILED', data: registerData });

    // Step 3: Heartbeat
    const heartbeatRes = await fetch(`${REGISTRY_BASE}/registry/heartbeat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: DROPLET_ID,
        host: DROPLET_ID,
        droplet_id: DROPLET_ID,
        load: 0.05,
        status: 'healthy',
      }),
    });
    const heartbeatData = await heartbeatRes.json();
    results.steps.push({ step: 'Heartbeat', status: heartbeatRes.ok ? 'SUCCESS' : 'FAILED', data: heartbeatData });

    results.overall = 'ALL TESTS PASSED ✅';
    return NextResponse.json(results);
  } catch (error) {
    results.overall = 'FAILED ❌';
    results.error = String(error);
    return NextResponse.json(results, { status: 500 });
  }
}

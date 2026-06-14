import { incrementRequestCount } from '../lib/udc';
import crypto from 'crypto';

export async function GET() {
  incrementRequestCount();
  
  // Generate proof hash
  const proofData = `5-${new Date().toISOString().split('T')[0]}`;
  const proof = crypto.createHash('sha256').update(proofData).digest('hex');
  
  const healthData = {
    id: 5,
    name: "Full Potential Dashboard",
    steward: "Haythem",
    status: "active",
    endpoint: "https://dashboard.fullpotential.ai",
    proof: proof,
    cost_usd: 0.05,
    yield_usd: 0.00,
    updated_at: new Date().toISOString()
  };
  
  return Response.json(healthData);
}

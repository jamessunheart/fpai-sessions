import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const response = await fetch('https://drop18.fullpotential.ai/health');
    const data = await response.json();
    
    return NextResponse.json({
      registry_reachable: response.ok,
      registry_health: data,
      droplet_id: 'drop5.fullpotential.ai',
      status: 'Registry client running in background'
    });
  } catch (error) {
    return NextResponse.json({
      registry_reachable: false,
      error: String(error)
    }, { status: 500 });
  }
}

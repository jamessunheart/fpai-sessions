import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const host = searchParams.get('host');
  
  if (!host) {
    return NextResponse.json({ error: 'Host required' }, { status: 400 });
  }

  try {
    const healthUrl = `https://${host}/health`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(healthUrl, { 
      signal: controller.signal,
      headers: { 'Accept': 'application/json' }
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      return NextResponse.json({ available: false, error: 'Unhealthy' }, { status: 200 });
    }
    
    const data = await response.json();
    return NextResponse.json({ ...data, available: true });
  } catch (error: any) {
    return NextResponse.json({ available: false, error: error.message }, { status: 200 });
  }
}

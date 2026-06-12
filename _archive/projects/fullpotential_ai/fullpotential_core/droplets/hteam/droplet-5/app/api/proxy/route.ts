import { NextRequest, NextResponse } from 'next/server';

const API_BASE = 'https://drop2.fullpotential.ai';
const REGISTRY_URL = 'https://drop18.fullpotential.ai';
const REGISTRY_API_KEY = process.env.REGISTRY_API_KEY || 'a5447df6e4fe34df8c4d0c671ad98ce78de9e55cf152e5d07e5bf221769e31dc';
const DROPLET_ID = 'drop5.fullpotential.ai';

let cachedToken: string | null = null;
let tokenExpiry: number = 0;

async function getRegistryToken(): Promise<string> {
  if (cachedToken && Date.now() < tokenExpiry) {
    return cachedToken;
  }

  const response = await fetch(`${REGISTRY_URL}/auth/token?droplet_id=${DROPLET_ID}`, {
    method: 'POST',
    headers: { 'X-Registry-Key': REGISTRY_API_KEY }
  });

  if (!response.ok) throw new Error('Failed to get token');
  
  const data = await response.json();
  cachedToken = data.token;
  tokenExpiry = Date.now() + 23 * 60 * 60 * 1000; // 23 hours
  return cachedToken;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint');
  
  if (!endpoint) {
    return NextResponse.json({ error: 'Endpoint required' }, { status: 400 });
  }

  try {
    let url;
    let headers: HeadersInit = {};
    
    if (endpoint.startsWith('/registry/')) {
      const token = await getRegistryToken();
      url = `${REGISTRY_URL}${endpoint}`;
      headers = { 'Authorization': `Bearer ${token}` };
    } else {
      url = `${API_BASE}${endpoint}`;
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    const response = await fetch(url, { 
      headers,
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    if (error.name === 'AbortError') {
      return NextResponse.json({ error: 'Request timeout' }, { status: 504 });
    }
    return NextResponse.json({ error: 'API request failed' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint');
  
  if (!endpoint) {
    return NextResponse.json({ error: 'Endpoint required' }, { status: 400 });
  }

  try {
    let body = null;
    try {
      body = await request.json();
    } catch {
      // No body or invalid JSON, continue with null body
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      ...(body && { body: JSON.stringify(body) }),
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'API request failed' }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint');
  
  if (!endpoint) {
    return NextResponse.json({ error: 'Endpoint required' }, { status: 400 });
  }

  try {
    const body = await request.json();
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'API request failed' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint');
  
  if (!endpoint) {
    return NextResponse.json({ error: 'Endpoint required' }, { status: 400 });
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'API request failed' }, { status: 500 });
  }
}
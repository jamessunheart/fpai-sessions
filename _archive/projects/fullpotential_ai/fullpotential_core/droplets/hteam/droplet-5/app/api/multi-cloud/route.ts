import { NextRequest, NextResponse } from 'next/server';

const API_BASE = 'https://drop4.fullpotential.ai';
const REGISTRY_URL = 'https://drop18.fullpotential.ai';
const REGISTRY_KEY = process.env.REGISTRY_API_KEY;

async function getFreshToken(): Promise<string> {
  try {
    const response = await fetch(
      `${REGISTRY_URL}/auth/token?droplet_id=drop4.fullpotential.ai`,
      { 
        method: 'POST',
        headers: { 'X-Registry-Key': REGISTRY_KEY! } 
      }
    );
    const data = await response.json();
    if (!data.token) {
      throw new Error(`Token fetch failed: ${JSON.stringify(data)}`);
    }
    return data.token;
  } catch (error) {
    console.error('Failed to get fresh token:', error);
    throw error;
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint') || '/multi/list';

  try {
    const token = await getFreshToken();
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 });
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
      // No body for action requests
    }

    const token = await getFreshToken();
    const fetchOptions: RequestInit = {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    };

    if (body) {
      fetchOptions.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, fetchOptions);
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to perform action' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const endpoint = searchParams.get('endpoint');
  
  if (!endpoint) {
    return NextResponse.json({ error: 'Endpoint required' }, { status: 400 });
  }

  try {
    const token = await getFreshToken();
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to delete' }, { status: 500 });
  }
}

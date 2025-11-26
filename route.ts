import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

const LEADS_DB = process.env.LEADS_DB_PATH ?? path.join(process.cwd(), 'var', 'leads.json');

export async function POST(req: Request) {
  try {
    const { email } = await req.json();
    
    if (!email || !email.includes('@')) {
      return NextResponse.json({ error: 'Invalid email' }, { status: 400 });
    }

    // Ensure directory exists
    await fs.mkdir(path.dirname(LEADS_DB), { recursive: true });

    // Read existing
    let leads = [];
    try {
      const data = await fs.readFile(LEADS_DB, 'utf-8');
      leads = JSON.parse(data);
    } catch (e) {
      // Ignore missing file
    }

    // Add new lead
    const newLead = {
      id: crypto.randomUUID(),
      email,
      source: 'magnet-sop',
      createdAt: new Date().toISOString(),
    };
    
    leads.push(newLead);

    // Write back
    await fs.writeFile(LEADS_DB, JSON.stringify(leads, null, 2));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Lead capture error:', error);
    return NextResponse.json({ error: 'Internal Error' }, { status: 500 });
  }
}







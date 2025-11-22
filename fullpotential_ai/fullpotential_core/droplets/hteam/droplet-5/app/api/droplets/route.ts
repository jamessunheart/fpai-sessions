import { NextResponse } from 'next/server';
import { fetchAllDroplets } from '@/app/lib/github-client';
import { parseReadme } from '@/app/lib/readme-parser';

export async function GET() {
  try {
    const droplets = await fetchAllDroplets();
    
    const parsed = droplets
      .map(({ repo, readme }) => parseReadme(readme.content, repo))
      .filter(d => d !== null);

    return NextResponse.json({
      success: true,
      count: parsed.length,
      droplets: parsed,
      timestamp: new Date().toISOString(),
    }, {
      headers: {
        'Cache-Control': 'no-store, max-age=0',
      },
    });
  } catch (error: any) {
    return NextResponse.json(
      { 
        success: false, 
        error: error.message 
      },
      { status: 500 }
    );
  }
}

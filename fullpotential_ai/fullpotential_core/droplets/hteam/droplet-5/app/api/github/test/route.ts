import { NextResponse } from 'next/server';
import { fetchReadme } from '@/app/lib/github-client';

export async function GET() {
  try {
    const readme = await fetchReadme('droplet-5');
    
    return NextResponse.json({
      success: true,
      repo: 'droplet-5',
      readme: {
        name: readme.name,
        path: readme.path,
        sha: readme.sha,
        contentLength: readme.content.length,
        preview: readme.content.substring(0, 500) + '...',
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

import { NextResponse } from 'next/server';
import { fetchReadme } from '@/app/lib/github-client';

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    const dropletId = params.id;
    const readme = await fetchReadme(`droplet-${dropletId}`);
    
    return NextResponse.json({
      success: true,
      dropletId,
      readme: readme.content,
      sha: readme.sha,
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

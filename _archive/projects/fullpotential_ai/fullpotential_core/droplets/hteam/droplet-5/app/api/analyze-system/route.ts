import { NextResponse } from 'next/server';
import { fetchAllDroplets } from '@/app/lib/github-client';
import { parseReadme } from '@/app/lib/readme-parser';

export const dynamic = 'force-dynamic';

export async function GET() {
  console.log('🔍 Analyze system endpoint called');
  try {
    console.log('📡 Fetching all droplets...');
    const droplets = await fetchAllDroplets();
    console.log(`✅ Fetched ${droplets.length} droplets`);
    
    console.log('🔬 Analyzing droplets...');
    const analysis = droplets.map(({ repo, readme }) => {
      console.log(`  Parsing ${repo}...`);
      const parsed = parseReadme(readme.content, repo);
      
      return {
        droplet: repo,
        status: parsed?.status || 'unknown',
        steward: parsed?.steward || 'unknown',
        compliance: parsed?.complianceScore || 'unknown',
        dependencies: parsed?.upstreamDependencies || [],
        issues: [],
        lastUpdated: 'unknown',
        readme: readme.content.substring(0, 500),
      };
    });
    
    const summary = {
      totalDroplets: analysis.length,
      operational: analysis.filter(d => d.status === 'OPERATIONAL').length,
      compliant: analysis.filter(d => d.compliance === '100%').length,
      withIssues: analysis.filter(d => d.issues.length > 0).length,
      droplets: analysis,
      systemHealth: {
        percentage: Math.round((analysis.filter(d => d.status === 'OPERATIONAL').length / analysis.length) * 100),
        status: 'healthy',
      },
    };
    
    console.log('✅ Analysis complete');
    return NextResponse.json(summary);
  } catch (error) {
    console.error('❌ Analysis failed:', error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}

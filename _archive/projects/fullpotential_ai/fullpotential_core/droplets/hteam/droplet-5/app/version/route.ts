import { NextRequest } from 'next/server';
import { incrementRequestCount, requireAuth, createUDCError } from '../lib/udc';

export async function GET(request: NextRequest) {
  try {
    requireAuth(request);
    incrementRequestCount();
    
    return Response.json({
      version: "1.0.0",
      build_date: "2025-11-08",
      commit_hash: "dev",
      environment: "development",
      deployed_by: "Haythem"
    });
  } catch (error: any) {
    return Response.json(
      createUDCError('UNAUTHORIZED', error.message || 'Authentication required'),
      { status: 401 }
    );
  }
}

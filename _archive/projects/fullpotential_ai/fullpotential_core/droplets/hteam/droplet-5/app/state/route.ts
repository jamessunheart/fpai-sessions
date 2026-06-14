import { NextRequest } from 'next/server';
import { getSystemState, incrementRequestCount, requireAuth, createUDCError } from '../lib/udc';

export async function GET(request: NextRequest) {
  try {
    requireAuth(request);
    incrementRequestCount();
    return Response.json(getSystemState());
  } catch (error: any) {
    return Response.json(
      createUDCError('UNAUTHORIZED', error.message || 'Authentication required'),
      { status: 401 }
    );
  }
}

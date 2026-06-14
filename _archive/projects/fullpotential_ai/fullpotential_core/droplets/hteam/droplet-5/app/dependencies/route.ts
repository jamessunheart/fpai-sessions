import { NextRequest } from 'next/server';
import { incrementRequestCount, requireAuth, createUDCError } from '../lib/udc';

export async function GET(request: NextRequest) {
  try {
    requireAuth(request);
    incrementRequestCount();
    
    return Response.json({
      required: [
        { id: 1, name: "Registry", status: "connected" },
        { id: 10, name: "Orchestrator", status: "connected" }
      ],
      optional: [
        { id: 2, name: "Airtable Connector", status: "available" },
        { id: 4, name: "Multi-Cloud Manager", status: "available" }
      ],
      missing: []
    });
  } catch (error: any) {
    return Response.json(
      createUDCError('UNAUTHORIZED', error.message || 'Authentication required'),
      { status: 401 }
    );
  }
}

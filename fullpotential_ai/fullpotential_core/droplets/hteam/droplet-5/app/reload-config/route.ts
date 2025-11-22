import { createUDCResponse, createUDCError, requireAuth, incrementRequestCount, incrementErrorCount } from '../lib/udc';
import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  incrementRequestCount();
  
  try {
    requireAuth(request);
    const body = await request.json();
    
    // Placeholder for config reload logic
    console.log('Reloading config from:', body.config_path || 'default');
    
    return Response.json({
      reloaded: true,
      config_path: body.config_path || '/default/config.json',
      reloaded_at: new Date().toISOString()
    });
  } catch (error) {
    incrementErrorCount();
    if (error instanceof Error && (error.message.includes('authorization') || error.message.includes('JWT'))) {
      return Response.json(
        createUDCError('UNAUTHORIZED', error.message),
        { status: 401 }
      );
    }
    return Response.json(
      createUDCError('INTERNAL_ERROR', 'Failed to reload config'),
      { status: 500 }
    );
  }
}

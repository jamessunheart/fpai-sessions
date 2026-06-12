import { createUDCResponse, createUDCError, requireAuth, incrementRequestCount, incrementErrorCount } from '../lib/udc';
import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  incrementRequestCount();
  
  try {
    requireAuth(request);
    const body = await request.json();
    
    const delaySeconds = body.delay_seconds || 10;
    const reason = body.reason || 'manual shutdown';
    
    console.log(`Graceful shutdown initiated: ${reason}, delay: ${delaySeconds}s`);
    
    // In a real implementation, you would initiate graceful shutdown here
    // setTimeout(() => process.exit(0), delaySeconds * 1000);
    
    return Response.json({
      shutdown_initiated: true,
      delay_seconds: delaySeconds,
      reason: reason,
      initiated_at: new Date().toISOString()
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
      createUDCError('INTERNAL_ERROR', 'Failed to initiate shutdown'),
      { status: 500 }
    );
  }
}

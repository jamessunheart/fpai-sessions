import { createUDCResponse, createUDCError, requireAuth, incrementRequestCount, incrementErrorCount } from '../lib/udc';
import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  incrementRequestCount();
  
  try {
    requireAuth(request);
    
    console.log('EMERGENCY STOP initiated');
    
    // In a real implementation, you would immediately stop the process
    // process.exit(1);
    
    return Response.json({
      emergency_stop: true,
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
      createUDCError('INTERNAL_ERROR', 'Failed to execute emergency stop'),
      { status: 500 }
    );
  }
}

import { createUDCResponse, createUDCError, requireAuth, incrementRequestCount, incrementErrorCount } from '../lib/udc';
import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  incrementRequestCount();
  
  try {
    requireAuth(request);
    const body = await request.json();
    
    // Validate required fields (including signature for dual authentication)
    const required = ['trace_id', 'source', 'target', 'message_type', 'payload', 'timestamp', 'signature'];
    for (const field of required) {
      if (!body[field]) {
        return Response.json(
          createUDCError('INVALID_REQUEST', `Missing required field: ${field}`),
          { status: 400 }
        );
      }
    }
    
    // Process the message (placeholder implementation)
    console.log('Received UDC message:', body);
    
    return Response.json({
      received: true,
      trace_id: body.trace_id,
      processed_at: new Date().toISOString(),
      result: "success"
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
      createUDCError('INTERNAL_ERROR', 'Failed to process message'),
      { status: 500 }
    );
  }
}

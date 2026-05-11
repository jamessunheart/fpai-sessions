import { createUDCResponse, createUDCError, requireAuth, incrementRequestCount, incrementErrorCount } from '../lib/udc';
import { NextRequest } from 'next/server';

export async function POST(request: NextRequest) {
  incrementRequestCount();
  
  try {
    requireAuth(request);
    const body = await request.json();
    
    // Validate required fields
    const required = ['target', 'message_type', 'payload'];
    for (const field of required) {
      if (!body[field]) {
        return Response.json(
          createUDCError('INVALID_REQUEST', `Missing required field: ${field}`),
          { status: 400 }
        );
      }
    }
    
    // Send message to target droplet (placeholder implementation)
    console.log('Sending UDC message to:', body.target, body);
    
    return Response.json({
      sent: true,
      target: body.target,
      trace_id: crypto.randomUUID(),
      status: "delivered"
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
      createUDCError('INTERNAL_ERROR', 'Failed to send message'),
      { status: 500 }
    );
  }
}

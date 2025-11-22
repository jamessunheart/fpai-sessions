import { NextRequest, NextResponse } from 'next/server';

// Store notifications in memory (for demo - use database in production)
let notifications: any[] = [];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Create notification
    const notification = {
      id: Date.now().toString(),
      type: 'proof',
      title: 'Sprint Completed',
      message: `Sprint ${body.sprint_id} completed by ${body.developer}`,
      timestamp: new Date(),
      read: false,
      data: body
    };
    
    // Store notification
    notifications.unshift(notification);
    notifications = notifications.slice(0, 50); // Keep max 50
    
    // Return success response
    return NextResponse.json({
      status: "proof received",
      data: {
        proof_id: body.proof_id,
        sprint_id: body.sprint_id,
        status: body.status,
        developer: body.developer
      }
    });
  } catch (error) {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }
}

export async function GET() {
  return NextResponse.json({ notifications });
}
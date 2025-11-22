import { NextRequest, NextResponse } from 'next/server';

// Store heartbeat notifications in memory (for demo - use database in production)
let heartbeatNotifications: any[] = [];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Create notification based on status
    let notificationType = 'heartbeat';
    let notificationTitle = 'System Status';
    let notificationMessage = `${body.cell_id} is ${body.status}`;
    
    if (body.status === 'warning' || (body.cpu && body.cpu > 90) || (body.memory && body.memory > 90)) {
      notificationType = 'warning';
      notificationTitle = 'Infrastructure Alert';
      notificationMessage = `${body.cell_id} - High resource usage (CPU: ${body.cpu}%, Memory: ${body.memory}%)`;
    } else if (body.status === 'offline' || body.status === 'down') {
      notificationType = 'error';
      notificationTitle = 'System Down';
      notificationMessage = `${body.cell_id} is offline and needs attention`;
    }
    
    // Store notification
    const notification = {
      id: Date.now().toString(),
      type: notificationType,
      title: notificationTitle,
      message: notificationMessage,
      timestamp: new Date(),
      read: false,
      data: body
    };
    
    heartbeatNotifications.unshift(notification);
    heartbeatNotifications = heartbeatNotifications.slice(0, 50); // Keep max 50
    
    // Return success response
    return NextResponse.json({
      status: "heartbeat received",
      data: {
        cell_id: body.cell_id,
        status: body.status
      }
    });
  } catch (error) {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }
}

export async function GET() {
  return NextResponse.json({ notifications: heartbeatNotifications });
}
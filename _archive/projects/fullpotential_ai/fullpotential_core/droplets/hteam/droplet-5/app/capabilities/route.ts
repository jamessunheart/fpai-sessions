import { NextRequest } from 'next/server';
import { incrementRequestCount, requireAuth, createUDCError } from '../lib/udc';

export async function GET(request: NextRequest) {
  try {
    requireAuth(request);
    incrementRequestCount();
    
    return Response.json({
      version: "1.0.0",
      features: [
        "real_time_monitoring",
        "dashboard_visualization",
        "sprint_management",
        "system_health_monitoring",
        "multi_cloud_integration"
      ],
      dependencies: ["registry", "orchestrator", "multi_cloud_manager"],
      udc_version: "1.0",
      metadata: {
        build_date: "2025-11-12",
        commit_hash: "latest"
      }
    });
  } catch (error: any) {
    return Response.json(
      createUDCError('UNAUTHORIZED', error.message || 'Authentication required'),
      { status: 401 }
    );
  }
}

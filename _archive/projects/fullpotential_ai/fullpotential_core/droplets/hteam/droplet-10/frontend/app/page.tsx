'use client';

import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

interface Sprint {
  id: number;
  droplet_name: string;
  status: string;
  created_at: string;
}

interface DashboardData {
  specs_pending: Sprint[];
  recruiting: Sprint[];
  build: Sprint[];
  verify: Sprint[];
  deploy: Sprint[];
  live: Sprint[];
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Fetch initial data
    fetchDashboard();

    // Connect WebSocket
    const socket = io(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
    
    socket.on('connect', () => {
      setConnected(true);
      console.log('WebSocket connected');
    });

    socket.on('sprint_updated', (update) => {
      console.log('Sprint updated:', update);
      fetchDashboard();
    });

    socket.on('sprint_created', (update) => {
      console.log('Sprint created:', update);
      fetchDashboard();
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/pipeline/dashboard`,
        {
          headers: {
            'Authorization': 'Bearer dev-token' // TODO: Real auth
          }
        }
      );
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    }
  };

  const renderColumn = (title: string, sprints: Sprint[], color: string) => (
    <div className="flex-1 min-w-[250px]">
      <div className={`p-4 rounded-t-lg ${color}`}>
        <h2 className="text-white font-bold">{title} ({sprints.length})</h2>
      </div>
      <div className="bg-gray-100 p-4 space-y-2 min-h-[400px]">
        {sprints.map((sprint) => (
          <div key={sprint.id} className="bg-white p-3 rounded shadow">
            <div className="font-semibold">#{sprint.id} {sprint.droplet_name}</div>
            <div className="text-sm text-gray-600">
              {new Date(sprint.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  if (!data) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Assembly Line Dashboard</h1>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>

        <div className="flex gap-4 overflow-x-auto">
          {renderColumn('Specs Pending', data.specs_pending, 'bg-yellow-600')}
          {renderColumn('Recruiting', data.recruiting, 'bg-blue-600')}
          {renderColumn('Build', data.build, 'bg-purple-600')}
          {renderColumn('Verify', data.verify, 'bg-orange-600')}
          {renderColumn('Deploy', data.deploy, 'bg-indigo-600')}
          {renderColumn('Live', data.live, 'bg-green-600')}
        </div>
      </div>
    </div>
  );
}
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

// --- Types ---

type NodeStatus = 'active' | 'inactive' | 'error';

interface SystemMapNode {
  id: string;
  label: string;
  type: string;
  status: NodeStatus;
  metadata?: Record<string, any>;
}

interface SystemMapEdge {
  id: string;
  source: string;
  target: string;
  status: NodeStatus;
}

interface SystemMapResponse {
  nodes: SystemMapNode[];
  edges: SystemMapEdge[];
  timestamp: string;
}

// --- Config ---

const POLL_INTERVAL_MS = 5000;
const REGISTRY_API_URL = '/registry/map'; // Assumes proxy or direct access

// --- Components ---

function NodeIcon({ type, status }: { type: string; status: NodeStatus }) {
  const colorClass =
    status === 'active' ? 'bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)]' :
    status === 'error' ? 'bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.5)]' :
    'bg-slate-500';

  return (
    <div className={`flex h-12 w-12 items-center justify-center rounded-full border-2 border-slate-900 ${colorClass} transition-all duration-500`}>
      <span className="text-xs font-bold text-slate-900 uppercase">
        {type.slice(0, 3)}
      </span>
    </div>
  );
}

export default function MapPage() {
  const [data, setData] = useState<SystemMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      // In a real app, this would be an environment variable
      const response = await fetch('http://localhost:8000/registry/map');
      if (!response.ok) throw new Error(`Failed to fetch map: ${response.statusText}`);
      const json = await response.json();
      setData(json);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Map fetch error:', err);
      // Keep old data if poll fails, but show error state
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  // --- Layout Logic (Star Topology) ---
  const layout = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };

    const width = 800;
    const height = 600;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 250;

    const nodesWithPos = data.nodes.map((node, i, arr) => {
      if (node.id === 'registry') {
        return { ...node, x: centerX, y: centerY };
      }
      
      // Distribute others in a circle
      // Filter out registry from the circle count to make it even
      const otherNodes = arr.filter(n => n.id !== 'registry');
      const indexInOthers = otherNodes.findIndex(n => n.id === node.id);
      const angle = (indexInOthers / otherNodes.length) * 2 * Math.PI - Math.PI / 2; // Start top
      
      return {
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    return { nodes: nodesWithPos, edges: data.edges };
  }, [data]);

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-white md:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-400">System Visibility</p>
            <h1 className="mt-2 text-4xl font-semibold">Live Autonomous Mesh</h1>
          </div>
          <div className="text-right">
             <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${error ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                <span className={`h-2 w-2 rounded-full ${error ? 'bg-red-500' : 'bg-emerald-500 animate-pulse'}`} />
                {error ? 'Connection Lost' : 'Live Stream'}
             </div>
             {lastUpdated && <p className="mt-1 text-xs text-slate-500">Last update: {lastUpdated.toLocaleTimeString()}</p>}
          </div>
        </header>

        <div className="mt-8 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 shadow-2xl backdrop-blur-sm">
          <div className="relative h-[600px] w-full">
            {loading && !data && (
               <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                 Initializing visualization...
               </div>
            )}

            {!loading && layout.nodes.length === 0 && (
               <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                 No active droplets found.
               </div>
            )}
            
            {/* SVG Layer for Edges */}
            <svg className="absolute inset-0 h-full w-full pointer-events-none">
              {layout.edges.map((edge) => {
                const source = layout.nodes.find(n => n.id === edge.source);
                const target = layout.nodes.find(n => n.id === edge.target);
                if (!source || !target) return null;

                const isError = edge.status === 'error';
                
                return (
                  <line
                    key={edge.id}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={isError ? '#ef4444' : '#10b981'}
                    strokeWidth={2}
                    strokeOpacity={0.4}
                    className="transition-all duration-500"
                  />
                );
              })}
            </svg>

            {/* HTML Layer for Nodes */}
            {layout.nodes.map((node) => (
              <div
                key={node.id}
                className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 transition-all duration-700 ease-out"
                style={{ left: node.x, top: node.y }}
              >
                <NodeIcon type={node.type} status={node.status} />
                <div className="flex flex-col items-center">
                   <span className="rounded bg-slate-950/80 px-2 py-0.5 text-xs font-medium text-white backdrop-blur-md">
                     {node.label}
                   </span>
                   {node.metadata?.version && (
                     <span className="text-[10px] text-slate-500">v{node.metadata.version}</span>
                   )}
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="mt-6 grid grid-cols-3 gap-4 text-center text-xs text-slate-500">
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
               <span className="block text-2xl font-bold text-emerald-400">{data?.nodes.length || 0}</span>
               Active Droplets
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
               <span className="block text-2xl font-bold text-white">{data?.edges.length || 0}</span>
               Mesh Connections
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
               <span className="block text-2xl font-bold text-emerald-400">100%</span>
               System Uptime
            </div>
        </div>
      </div>
    </main>
  );
}


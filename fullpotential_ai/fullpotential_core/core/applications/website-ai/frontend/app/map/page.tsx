'use client';

import { useEffect, useMemo, useState } from "react";
import styles from "./map.module.css";

type NodeStatus = "active" | "inactive" | "error";

interface RegistryNode {
  id: string;
  name: string;
  status: NodeStatus;
  type?: string;
  metadata?: Record<string, any>;
}

interface RegistryEdge {
  from: string;
  to: string;
}

interface RegistryMapResponse {
  nodes: RegistryNode[];
  edges: RegistryEdge[];
  timestamp?: string;
  source?: string;
  metadata?: {
    generated_at?: string;
    registered_total?: number;
  };
}

interface PositionedNode extends RegistryNode {
  x: number;
  y: number;
}

const POLL_INTERVAL_MS = 5000;
const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 560;
const CENTER_NODE_ID = "registry";

export default function MapPage() {
  const [data, setData] = useState<RegistryMapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch("/registry/map", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Registry map returned ${response.status}`);
        }
        const payload = (await response.json()) as RegistryMapResponse;
        if (!cancelled) {
          setData(payload);
          setError(null);
          setLastUpdated(new Date());
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to reach the registry endpoint.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const layout = useMemo(() => {
    if (!data) {
      return { nodes: [] as PositionedNode[], edges: [] as RegistryEdge[] };
    }

    const center = data.nodes.find((node) => node.id === CENTER_NODE_ID);
    const others = data.nodes
      .filter((node) => node.id !== CENTER_NODE_ID)
      .sort((a, b) => a.id.localeCompare(b.id));
    const nodes: PositionedNode[] = [];

    if (center) {
      nodes.push({ ...center, x: CANVAS_WIDTH / 2, y: CANVAS_HEIGHT / 2 });
    }

    const radius = Math.min(CANVAS_WIDTH, CANVAS_HEIGHT) / 2 - 90;
    others.forEach((node, index) => {
      const angle =
        others.length === 0
          ? 0
          : (index / others.length) * Math.PI * 2 - Math.PI / 2;
      nodes.push({
        ...node,
        x: CANVAS_WIDTH / 2 + radius * Math.cos(angle),
        y: CANVAS_HEIGHT / 2 + radius * Math.sin(angle),
      });
    });

    // If there was no registry node, distribute everyone evenly.
    if (!center && data.nodes.length > 0 && nodes.length === 0) {
      const fallbackNodes = [...data.nodes].sort((a, b) =>
        a.id.localeCompare(b.id),
      );
      fallbackNodes.forEach((node, index) => {
        const angle =
          (index / fallbackNodes.length) * Math.PI * 2 - Math.PI / 2;
        nodes.push({
          ...node,
          x: CANVAS_WIDTH / 2 + radius * Math.cos(angle),
          y: CANVAS_HEIGHT / 2 + radius * Math.sin(angle),
        });
      });
    }

    return { nodes, edges: data.edges };
  }, [data]);

  const positionedMap = useMemo(() => {
    const map = new Map<string, PositionedNode>();
    layout.nodes.forEach((node) => map.set(node.id, node));
    return map;
  }, [layout.nodes]);

  const activeNodes = data?.nodes.filter((node) => node.status === "active").length ?? 0;
  const edgeCount = data?.edges.length ?? 0;

  const statusClass = (status: NodeStatus) => {
    if (status === "active") return `${styles.nodeIcon} ${styles.nodeIconActive}`;
    if (status === "error") return `${styles.nodeIcon} ${styles.nodeIconError}`;
    return `${styles.nodeIcon} ${styles.nodeIconInactive}`;
  };

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.header}>
          <div>
            <div className={styles.statusChip}>
              <span className={styles.statusDot} />
              Autonomous Mesh
            </div>
            <h1 style={{ marginTop: "0.75rem", marginBottom: "0.2rem" }}>
              Droplet Mesh Topology
            </h1>
            <p style={{ color: "#cbd5f5", maxWidth: "560px", lineHeight: 1.6 }}>
              Live rendering of the Registry, Orchestrator, Magnet, and
              Storefront droplets plus any newly registered nodes. Every edge
              represents a dependency published through the Universal Droplet
              Contract.
            </p>
          </div>
          <div>
            {lastUpdated && (
              <p className={styles.timestamp}>
                Last refresh: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
            {data?.source && (
              <p className={styles.timestamp}>
                Topology version: {data.source}
              </p>
            )}
          </div>
        </div>

        <div className={styles.card}>
          <div className={styles.canvas}>
            {loading && (
              <div className={styles.loading}>Initializing visualization…</div>
            )}
            {!loading && layout.nodes.length === 0 && (
              <div className={styles.emptyState}>No droplets detected.</div>
            )}

            <svg
              className={styles.edgesLayer}
              width={CANVAS_WIDTH}
              height={CANVAS_HEIGHT}
            >
              {layout.edges.map((edge) => {
                const source = positionedMap.get(edge.from);
                const target = positionedMap.get(edge.to);
                if (!source || !target) {
                  return null;
                }
                const isError =
                  source.status === "error" || target.status === "error";
                return (
                  <line
                    key={`${edge.from}->${edge.to}`}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={isError ? "#f87171" : "#34d399"}
                    strokeWidth={2}
                    strokeOpacity={0.35}
                  />
                );
              })}
            </svg>

            {layout.nodes.map((node) => (
              <div
                key={node.id}
                className={styles.node}
                style={{ left: node.x, top: node.y }}
              >
                <div className={statusClass(node.status)}>
                  {(node.type || node.name).slice(0, 3)}
                </div>
                <div className={styles.nodeLabel}>{node.name}</div>
                {node.metadata?.version && (
                  <span className={styles.nodeVersion}>
                    v{node.metadata.version}
                  </span>
                )}
              </div>
            ))}
          </div>

          {error && (
            <div className={styles.errorBanner}>
              Connection degraded: {error}. Showing the last known topology.
            </div>
          )}

          <div className={styles.stats}>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Active Droplets</div>
              <div
                className={`${styles.statValue} ${styles.statValueAccent}`}
              >
                {activeNodes}
              </div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Mesh Connections</div>
              <div className={styles.statValue}>{edgeCount}</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Registered Total</div>
              <div className={styles.statValue}>
                {data?.metadata?.registered_total ?? "—"}
              </div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Data Source</div>
              <div className={styles.statValue}>
                {data?.source ? data.source : "udc_config"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


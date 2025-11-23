'use client';

import { useEffect, useState } from "react";

type Mission = {
  id: string;
  title: string;
  priority?: string;
  owner?: string;
  principle?: string;
  status?: string;
};

const MISSION_FEED_URL = "/docs/status/missions.json";

export default function HomePage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMissions() {
      try {
        const response = await fetch(MISSION_FEED_URL, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Mission feed returned ${response.status}`);
        }
        const json = await response.json();
        if (!cancelled) {
          setMissions(Array.isArray(json?.missions) ? json.missions : []);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Unable to load mission feed.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadMissions();
    return () => {
      cancelled = true;
    };
  }, []);

  const openMissions = missions.filter((mission) => mission.status === "OPEN");

  return (
    <main className="home">
      <div className="panel">
        <header>
          <p className="status-pill">
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "999px",
                background: "#22c55e",
              }}
            />
            Live System Stream
          </p>
          <h1>Full Potential AI</h1>
          <p>The Operating System for Paradise Economics.</p>
          <p>
            <strong>Researching:</strong> AI Consciousness · Autonomous
            Coordination · Regenerative Finance.
          </p>
          <p>
            <em>Status:</em> System Active · Town Crier + Nexus aligned to the
            Constitution.
          </p>
        </header>

        <ul>
          <li>
            <strong>We create</strong> regenerative feedback loops instead of
            extractive funnels.
          </li>
          <li>
            <strong>We liberate</strong> the Architect and mission runners
            through autonomous tooling.
          </li>
          <li>
            <strong>We elevate</strong> awareness — every deployment must expand
            consciousness.
          </li>
        </ul>

        <div className="links">
          <a
            href="https://github.com/jamessunheart/fpai-sessions/blob/main/fullpotential_core/core/knowledge/CONSTITUTION.md"
            target="_blank"
            rel="noreferrer"
          >
            🕊 Full Potential Constitution — guiding principles for every
            mission.
          </a>
          <a
            href="https://github.com/jamessunheart/fpai-sessions/blob/main/fullpotential_core/core/knowledge/PAPERS_INDEX.md"
            target="_blank"
            rel="noreferrer"
          >
            📚 Papers Index — 300+ research PDFs including the 180-page legal
            blueprint for regenerative orgs.
          </a>
          <a
            href="https://github.com/jamessunheart/fpai-sessions/tree/main/fullpotential_core/docs/papers/%F0%9F%93%98180pgChurch_Legal_Resource.pdf"
            target="_blank"
            rel="noreferrer"
          >
            ⚖️ Church &amp; Civic Legal Toolkit — reference for compliant
            regenerative structures.
          </a>
        </div>

        <section className="mission-board">
          <h2>Live Mission Board</h2>
          <p style={{ color: "var(--text)" }}>
            The Nervous System publishes every mission here. Filter by priority
            directly in the UI.
          </p>

          {loading && <p>Loading mission feed…</p>}
          {!loading && error && (
            <p style={{ color: "#f87171" }}>
              Unable to load mission feed: {error}. Check Town Crier logs.
            </p>
          )}
          {!loading && !error && openMissions.length === 0 && (
            <p style={{ color: "var(--text)" }}>No missions detected.</p>
          )}

          {!loading && !error && openMissions.length > 0 && (
            <table className="mission-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Mission</th>
                  <th>Priority</th>
                  <th>Owner</th>
                  <th>Principle</th>
                </tr>
              </thead>
              <tbody>
                {openMissions.map((mission) => {
                  const priority = (mission.priority || "").toLowerCase();
                  const priorityClass =
                    priority === "p0"
                      ? "priority-chip p0"
                      : priority === "p1"
                        ? "priority-chip p1"
                        : "priority-chip default";
                  return (
                    <tr key={mission.id}>
                      <td>{mission.id}</td>
                      <td>{mission.title}</td>
                      <td className={priorityClass}>
                        {mission.priority || "-"}
                      </td>
                      <td>{mission.owner || "UNASSIGNED"}</td>
                      <td>{mission.principle || "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </main>
  );
}


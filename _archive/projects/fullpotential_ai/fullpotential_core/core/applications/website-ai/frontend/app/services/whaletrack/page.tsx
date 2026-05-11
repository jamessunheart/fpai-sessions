import Link from "next/link";

const stats = [
  { label: "Port", value: "8600" },
  { label: "Status", value: "✅ Online" },
  { label: "Mode", value: "Paper + Live" },
  { label: "Verifier", value: "34 tests" },
];

const magnetHighlights = [
  "Magnet scanner w/ 0-100 scoring",
  "Whale state engine (UP / DOWN / FOG)",
  "Flow map to pick the cheapest magnet",
  "Entry + exit engines with R:R guardrails",
  "Reversal detection post sweep",
  "UDC-compliant FastAPI surface",
];

const endpoints = [
  { route: "/api/whale/update", info: "POST candles + liquidity context" },
  { route: "/api/whale/status", info: "Current whale direction + confidence" },
  { route: "/api/magnets/current", info: "Active magnet stack" },
  { route: "/api/signals/entry", info: "Latest alignment signals" },
  { route: "/api/signals/exit", info: "Exit / safety instructions" },
  { route: "/api/position/current", info: "Live position snapshot" },
];

const bridgeSteps = [
  "Clone whaletrack-magnetic-trader",
  "pip install -r bridge/requirements.txt",
  "export WHALETRACK_API_BASE=http://198.54.123.234:8600",
  "export BRIDGE_EXCHANGE=kraken",
  "python bridge/bridge_service.py",
];

export default function WhaleTrackPage() {
  return (
    <main className="services-page">
      <div className="panel">
        <Link href="/services" className="status-pill" style={{ marginBottom: "1.5rem" }}>
          ← back to services
        </Link>
        <header className="services-hero" style={{ marginBottom: "1.5rem" }}>
          <p className="status-pill">Markets / Liquidity Engine</p>
          <h1>WhaleTrack</h1>
          <p>
            The magnetic trading system that hunts liquidity rooms. It reads whale direction,
            scores every magnet, and rides the cheapest path. Deployed on the live box and
            emitting signals at port 8600.
          </p>
        </header>

        <section className="detail-panel">
          <h2>Live Status</h2>
          <p style={{ marginTop: "0.25rem" }}>
            God Mode is watching this droplet and forwarding health, capabilities, state,
            dependencies, and heartbeat data. Treasury + Nexus follow its output to rank
            trades.
          </p>
          <div className="stats-grid">
            {stats.map((stat) => (
              <div key={stat.label} className="stat">
                <small>{stat.label}</small>
                <strong>{stat.value}</strong>
              </div>
            ))}
          </div>
          <div className="cta-row">
            <a href="https://198.54.123.234:8600/health" target="_blank" rel="noreferrer">
              API Health
            </a>
            <a
              href="https://198.54.123.234:8600/api/whale/status"
              target="_blank"
              rel="noreferrer"
            >
              Whale Status
            </a>
            <a
              href="https://github.com/fullpotential-ai/whaletrack-magnetic-trader"
              target="_blank"
              rel="noreferrer"
            >
              GitHub Repo
            </a>
          </div>
        </section>

        <section className="detail-layout">
          <div className="detail-panel">
            <h3>Trading loop</h3>
            <p>
              WhaleTrack executes a disciplined loop that mirrors the spec. Each signal has a
              reason string + minimum confidence before the bridge is allowed to act.
            </p>
            <ul style={{ marginTop: "1rem" }}>
              <li>Identify whale direction + sweeps.</li>
              <li>Scan / score magnets (equal highs, liquidations, HVNs, FVGs).</li>
              <li>Calculate flow → choose lowest energy path.</li>
              <li>Wait for alignment → momentum / retrace / reversal entry.</li>
              <li>Exit at magnet, front-run, or sweep snapback.</li>
              <li>Watch for reversals and flip when warranted.</li>
            </ul>
            <div className="tag-grid">
              {magnetHighlights.map((item) => (
                <span key={item} className="tag">
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-panel">
            <h3>Bridge service</h3>
            <p>
              The bridge keeps WhaleTrack fed with live candles and logs paper trades. Swap
              exchanges via env vars (Kraken, KuCoin, Bybit…) and move from paper → live.
            </p>
            <ol style={{ marginTop: "1rem", color: "var(--text)", paddingLeft: "1.2rem" }}>
              {bridgeSteps.map((step) => (
                <li key={step} style={{ marginBottom: "0.35rem" }}>
                  <code>{step}</code>
                </li>
              ))}
            </ol>
            <p style={{ marginTop: "1rem" }}>
              Trades are logged to <code>bridge/paper_trades.json</code> inside the repo (link
              below). The same scaffolding will execute live orders once API keys are injected.
            </p>
            <div className="link-grid">
              <a
                href="https://github.com/fullpotential-ai/whaletrack-magnetic-trader/blob/main/bridge/bridge_service.py"
                target="_blank"
                rel="noreferrer"
              >
                🔧 Bridge Source
              </a>
              <a
                href="https://github.com/fullpotential-ai/whaletrack-magnetic-trader/blob/main/bridge/paper_trades.json"
                target="_blank"
                rel="noreferrer"
              >
                📈 Paper Trade Log
              </a>
            </div>
          </div>
        </section>

        <section className="detail-panel" style={{ marginTop: "1.5rem" }}>
          <h3>UDC Surface</h3>
          <p>
            Every droplet exposes the five required endpoints plus trading-specific APIs. Call
            them directly or let Gatekeeper route.
          </p>
          <div style={{ marginTop: "1rem" }}>
            {endpoints.map((endpoint) => (
              <div
                key={endpoint.route}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid rgba(255,255,255,0.08)",
                  padding: "0.6rem 0",
                  gap: "1rem",
                }}
              >
                <code>{endpoint.route}</code>
                <span style={{ color: "#94a3b8", fontSize: "0.9rem" }}>{endpoint.info}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}


"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, endpoints, type Escalation } from "@/lib/api";

type Offer = { escalation_id: string; receivedAt: number };

export default function AgentConsole() {
  const [agentId, setAgentId]     = useState<string>("");
  const [connected, setConnected] = useState(false);
  const [offers, setOffers]       = useState<Offer[]>([]);
  const [active, setActive]       = useState<Escalation | null>(null);
  const [draft, setDraft]         = useState("");
  const [log, setLog]             = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!agentId) return;
    const ws = new WebSocket(endpoints.agentSocket(agentId));
    wsRef.current = ws;
    ws.onopen     = () => { setConnected(true); log_("connected"); };
    ws.onclose    = () => { setConnected(false); log_("disconnected"); };
    ws.onerror    = ()  => log_("error");
    ws.onmessage  = e   => {
      try {
        const m = JSON.parse(e.data);
        if (m.type === "offer") {
          setOffers(prev => [{ escalation_id: m.escalation_id, receivedAt: Date.now() }, ...prev]);
        } else if (m.type === "hello" || m.type === "pong") {
          log_(m.type);
        }
      } catch {}
    };
    const ping = setInterval(() => { if (ws.readyState === 1) ws.send(JSON.stringify({ type: "ping" })); }, 15_000);
    return () => { clearInterval(ping); ws.close(); };
  }, [agentId]);

  function log_(s: string) {
    setLog(prev => [new Date().toISOString().slice(11, 19) + "  " + s, ...prev].slice(0, 50));
  }

  async function accept(id: string) {
    try {
      await api<unknown>(endpoints.acceptOffer(id), {
        method: "POST",
        body: JSON.stringify({ escalation_id: id, agent_id: agentId }),
      });
      const esc = await api<Escalation>(endpoints.escalation(id));
      setActive(esc);
      setOffers(prev => prev.filter(o => o.escalation_id !== id));
      log_(`accepted ${id.slice(0, 8)}`);
    } catch (e: any) {
      log_(`accept failed: ${e.message}`);
    }
  }

  const headerStatus = useMemo(() => {
    if (!agentId) return { label: "sign in", color: "text-white/40" };
    if (connected) return { label: "live", color: "text-good" };
    return { label: "offline", color: "text-danger" };
  }, [agentId, connected]);

  return (
    <div className="h-screen grid grid-rows-[48px_1fr] bg-ink text-white">
      <header className="flex items-center justify-between px-4 border-b border-white/10">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-semibold text-accent">Concierge · Agent Console</span>
          <span className="text-white/30">/</span>
          <span className={headerStatus.color}>{headerStatus.label}</span>
        </div>
        <div className="flex items-center gap-2">
          <input
            placeholder="agent_id (uuid)"
            value={agentId}
            onChange={e => setAgentId(e.target.value.trim())}
            className="bg-panel text-xs px-2 py-1 rounded border border-white/10 w-72"
          />
        </div>
      </header>

      <main className="grid grid-cols-[300px_1fr_340px] gap-px bg-white/5 overflow-hidden">
        {/* Queue */}
        <section className="bg-ink flex flex-col">
          <h2 className="px-3 py-2 text-xs uppercase tracking-wider text-white/40 border-b border-white/10">Queue</h2>
          <ul className="flex-1 overflow-auto">
            {offers.length === 0 && <li className="px-3 py-4 text-xs text-white/30">No pending offers.</li>}
            {offers.map(o => (
              <li key={o.escalation_id} className="px-3 py-2 border-b border-white/5">
                <div className="text-xs font-mono text-accent">{o.escalation_id.slice(0, 8)}</div>
                <div className="text-[10px] text-white/40 mb-1">{new Date(o.receivedAt).toLocaleTimeString()}</div>
                <button
                  onClick={() => accept(o.escalation_id)}
                  className="w-full text-xs px-2 py-1 rounded bg-accent/10 hover:bg-accent/20 text-accent border border-accent/20"
                >
                  Accept
                </button>
              </li>
            ))}
          </ul>
        </section>

        {/* Active conversation */}
        <section className="bg-ink flex flex-col">
          <h2 className="px-3 py-2 text-xs uppercase tracking-wider text-white/40 border-b border-white/10">
            Active conversation
          </h2>
          <div className="flex-1 overflow-auto p-4">
            {!active ? (
              <p className="text-xs text-white/30">Accept an offer to start helping a caller.</p>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-white/40">Escalation</div>
                <pre className="text-xs bg-panel p-3 rounded border border-white/10 overflow-auto">{JSON.stringify(active, null, 2)}</pre>
                {active.agent_phone && (
                  <div className="text-xs text-good">Transfer sent to {active.agent_phone}</div>
                )}
              </div>
            )}
          </div>

          {/* Draft */}
          <div className="border-t border-white/10 p-3 space-y-2">
            <div className="text-[11px] uppercase tracking-wider text-white/40">AI draft (edit to train)</div>
            <textarea
              value={draft}
              onChange={e => setDraft(e.target.value)}
              placeholder="The AI draft will appear here in M3. Edits are captured as training signal."
              className="w-full h-20 bg-panel border border-white/10 rounded px-2 py-1 text-sm"
            />
            <div className="flex justify-end gap-2">
              <button className="text-xs px-3 py-1 rounded border border-white/15 hover:bg-white/5">Discard</button>
              <button className="text-xs px-3 py-1 rounded bg-accent text-ink font-medium hover:bg-accent/90">Send</button>
            </div>
          </div>
        </section>

        {/* Tools + log */}
        <aside className="bg-ink flex flex-col">
          <h2 className="px-3 py-2 text-xs uppercase tracking-wider text-white/40 border-b border-white/10">Tools</h2>
          <div className="p-3 space-y-2 text-xs">
            <button className="w-full text-left px-2 py-1 rounded border border-white/10 hover:bg-white/5">Book appointment…</button>
            <button className="w-full text-left px-2 py-1 rounded border border-white/10 hover:bg-white/5">Send quote…</button>
            <button className="w-full text-left px-2 py-1 rounded border border-white/10 hover:bg-white/5">Escalate to supervisor</button>
            <button className="w-full text-left px-2 py-1 rounded border border-white/10 hover:bg-white/5">Lookup knowledge base</button>
          </div>
          <h2 className="px-3 py-2 text-xs uppercase tracking-wider text-white/40 border-y border-white/10 mt-auto">Event log</h2>
          <ul className="p-2 text-[11px] font-mono overflow-auto max-h-56">
            {log.map((l, i) => <li key={i} className="text-white/60 py-0.5">{l}</li>)}
          </ul>
        </aside>
      </main>
    </div>
  );
}

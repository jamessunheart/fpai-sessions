"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { api, endpoints } from "@/lib/api";

type StatusOut = {
  status: string;
  plan: string;
  phone_numbers_configured: number;
  knowledge_sources: { total: number; indexed: number };
  active_voice_pack: boolean;
  ready_for_calls: boolean;
};

type FeatureMap = {
  tenant_id: string;
  plan: string;
  features: Record<string, { enabled: boolean; source: string }>;
};

const fetcher = <T,>(url: string, tid: string) =>
  api<T>(url, { tenantId: tid });

function DashboardInner() {
  const params = useSearchParams();
  const [tid, setTid] = useState<string>("");

  useEffect(() => {
    const q = params.get("tid");
    if (q) setTid(q);
  }, [params]);

  const { data: status, error: se } = useSWR<StatusOut>(
    tid ? [endpoints.status(tid), tid] : null,
    ([u, t]: [string, string]) => fetcher<StatusOut>(u, t),
    { refreshInterval: 10_000 },
  );
  const { data: feats } = useSWR<FeatureMap>(
    tid ? [endpoints.features(tid), tid] : null,
    ([u, t]: [string, string]) => fetcher<FeatureMap>(u, t),
    { refreshInterval: 30_000 },
  );

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Concierge · Dashboard</h1>
          <input
            className="input max-w-xs"
            placeholder="tenant_id"
            value={tid}
            onChange={e => setTid(e.target.value.trim())}
          />
        </header>

        {!tid && (
          <div className="card p-6 text-slate-500">Enter your tenant_id above to see live status.</div>
        )}

        {tid && (
          <>
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Stat label="Status"            value={status?.status ?? "…"} />
              <Stat label="Plan"              value={status?.plan ?? "…"} />
              <Stat label="Numbers"           value={status?.phone_numbers_configured ?? 0} />
              <Stat
                label="Knowledge indexed"
                value={`${status?.knowledge_sources.indexed ?? 0}/${status?.knowledge_sources.total ?? 0}`}
              />
            </section>

            <section className="card p-6 space-y-2">
              <h2 className="font-semibold">Ready for calls?</h2>
              <p className={`text-sm ${status?.ready_for_calls ? "text-good" : "text-warn"}`}>
                {status?.ready_for_calls
                  ? "Yes — forward your business line to your trial number."
                  : "Not yet — finish the onboarding steps above."}
              </p>
            </section>

            <section className="card p-6">
              <h2 className="font-semibold mb-3">Features</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {feats && Object.entries(feats.features).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between px-3 py-2 border border-slate-200 rounded-md text-sm">
                    <span>{k}</span>
                    <span className={`text-xs ${v.enabled ? "text-good" : "text-slate-400"}`}>
                      {v.enabled ? "on" : "off"} · {v.source}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {se && <p className="text-danger text-sm">{String(se)}</p>}
          </>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen p-6 text-slate-500">Loading dashboard…</div>
      }
    >
      <DashboardInner />
    </Suspense>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card p-4">
      <div className="label">{label}</div>
      <div className="text-xl font-semibold mt-1">{value}</div>
    </div>
  );
}

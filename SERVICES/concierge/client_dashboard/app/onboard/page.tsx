"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, endpoints } from "@/lib/api";

type Step = 1 | 2 | 3 | 4;

const INDUSTRIES = [
  { id: "home_services.hvac", label: "HVAC" },
  { id: "home_services.plumbing", label: "Plumbing" },
  { id: "home_services.electrical", label: "Electrical" },
  { id: "legal.personal_injury_intake", label: "Legal intake" },
  { id: "other", label: "Other" },
];

export default function Onboard() {
  const router = useRouter();
  const [step, setStep]     = useState<Step>(1);
  const [slug, setSlug]     = useState("");
  const [name, setName]     = useState("");
  const [email, setEmail]   = useState("");
  const [industry, setInd]  = useState(INDUSTRIES[0].id);
  const [urls, setUrls]     = useState("");
  const [tid, setTid]       = useState<string | null>(null);
  const [phone, setPhone]   = useState<string | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const [busy, setBusy]     = useState(false);

  async function doStart() {
    setBusy(true); setError(null);
    try {
      const out = await api<{ tenant_id: string; slug: string }>(endpoints.start(), {
        method: "POST",
        body: JSON.stringify({
          slug, name, industry,
          admin_email: email,
          admin_name: name,
        }),
      });
      setTid(out.tenant_id);
      setStep(2);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function doKnowledge() {
    if (!tid) return;
    setBusy(true); setError(null);
    try {
      const list = urls.split(/[\s,]+/).map(u => u.trim()).filter(Boolean);
      await api<unknown>(endpoints.knowledge(tid), {
        method: "POST", tenantId: tid,
        body: JSON.stringify({ urls: list }),
      });
      setStep(3);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function doPhone() {
    if (!tid) return;
    setBusy(true); setError(null);
    try {
      const out = await api<{ phone_e164: string }>(endpoints.phoneTrial(tid), {
        method: "POST", tenantId: tid,
      });
      setPhone(out.phone_e164);
      setStep(4);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function doCheckout() {
    if (!tid) return;
    setBusy(true); setError(null);
    try {
      const out = await api<{ url?: string; checkout_url?: string }>(endpoints.checkout(tid), {
        method: "POST", tenantId: tid,
        body: JSON.stringify({
          sku: "concierge.starter.monthly",
          success_url: `${window.location.origin}/dashboard?tid=${tid}`,
          cancel_url:  `${window.location.origin}/onboard`,
        }),
      });
      const target = out.url ?? out.checkout_url;
      if (target) window.location.href = target;
      else router.push(`/dashboard?tid=${tid}`);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <Header step={step} />
        <div className="card p-6 space-y-4">
          {step === 1 && (
            <section className="space-y-3">
              <Labeled label="Business name">
                <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Demo HVAC Co." />
              </Labeled>
              <Labeled label="Slug (unique, URL-safe)">
                <input className="input" value={slug} onChange={e => setSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"))} placeholder="demo-hvac" />
              </Labeled>
              <Labeled label="Admin email">
                <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="owner@demo.com" />
              </Labeled>
              <Labeled label="Industry">
                <select className="input" value={industry} onChange={e => setInd(e.target.value)}>
                  {INDUSTRIES.map(i => <option key={i.id} value={i.id}>{i.label}</option>)}
                </select>
              </Labeled>
              <div className="flex justify-end">
                <button className="btn-primary disabled:opacity-50" disabled={busy || !slug || !name || !email} onClick={doStart}>
                  {busy ? "Creating…" : "Create tenant"}
                </button>
              </div>
            </section>
          )}

          {step === 2 && (
            <section className="space-y-3">
              <Labeled label="Point us at your URL(s)">
                <textarea className="input min-h-28" value={urls} onChange={e => setUrls(e.target.value)} placeholder="https://your-site.com\nhttps://your-site.com/pricing" />
              </Labeled>
              <p className="text-xs text-slate-500">We'll crawl, chunk, and embed — your concierge will answer from this content within minutes.</p>
              <div className="flex justify-between">
                <button className="btn-secondary" onClick={() => setStep(3)}>Skip for now</button>
                <button className="btn-primary disabled:opacity-50" disabled={busy || !urls.trim()} onClick={doKnowledge}>
                  {busy ? "Submitting…" : "Submit and continue"}
                </button>
              </div>
            </section>
          )}

          {step === 3 && (
            <section className="space-y-3">
              <p className="text-sm">We'll reserve a trial Twilio number you can forward your main line to.</p>
              <div className="flex justify-end">
                <button className="btn-primary disabled:opacity-50" disabled={busy} onClick={doPhone}>
                  {busy ? "Allocating…" : "Allocate trial number"}
                </button>
              </div>
            </section>
          )}

          {step === 4 && (
            <section className="space-y-3">
              {phone && (
                <p className="text-sm">
                  Your trial number: <span className="font-mono font-semibold">{phone}</span>.
                  Forward your main number here (or call it directly to test).
                </p>
              )}
              <p className="text-sm text-slate-600">
                Start your <span className="font-medium">Starter plan</span> (199 UC/mo) — cancel anytime.
              </p>
              <div className="flex justify-between">
                <button className="btn-secondary" onClick={() => router.push(`/dashboard?tid=${tid}`)}>Skip to dashboard</button>
                <button className="btn-primary disabled:opacity-50" disabled={busy} onClick={doCheckout}>
                  {busy ? "Redirecting…" : "Start subscription"}
                </button>
              </div>
            </section>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}
        </div>
      </div>
    </div>
  );
}

function Header({ step }: { step: Step }) {
  const steps = ["Tenant", "Knowledge", "Phone", "Plan"];
  return (
    <div className="flex items-center gap-3">
      {steps.map((s, i) => {
        const n = (i + 1) as Step;
        const active = n <= step;
        return (
          <div key={s} className="flex items-center gap-3">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${active ? "bg-accent text-white" : "bg-slate-200 text-slate-500"}`}>{n}</div>
            <span className={`text-sm ${active ? "text-slate-800" : "text-slate-400"}`}>{s}</span>
            {i < steps.length - 1 && <div className="w-10 h-px bg-slate-200" />}
          </div>
        );
      })}
    </div>
  );
}

function Labeled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="label">{label}</div>
      {children}
    </div>
  );
}

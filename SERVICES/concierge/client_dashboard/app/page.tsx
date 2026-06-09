"use client";

import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-xl w-full card p-8 space-y-6 text-center">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-400">Full Potential</div>
          <h1 className="text-3xl font-semibold mt-1">Concierge</h1>
          <p className="text-slate-500 mt-2">
            An AI-first answering service that books jobs for you. Set up in 30 minutes.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Link href="/onboard" className="btn-primary">Start onboarding</Link>
          <Link href="/dashboard" className="btn-secondary">Sign in</Link>
        </div>

        <ul className="text-sm text-slate-500 space-y-1 pt-4 border-t border-slate-200">
          <li>Your URL → smart answers (no prompting by you)</li>
          <li>Twilio trial number in one click</li>
          <li>Pay only for what the AI actually delivers</li>
        </ul>
      </div>
    </div>
  );
}

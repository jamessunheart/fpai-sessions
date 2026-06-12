import Link from 'next/link';
import { LeadCapture } from '@/components/LeadCapture';

export default function FreeSopPage() {
  return (
    <main className="min-h-screen bg-white text-black">
      <div className="max-w-3xl mx-auto px-6 py-24 space-y-12">
        <header className="space-y-6 text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-gray-400">Free Resource</p>
          <h1 className="text-5xl font-black tracking-tight">The Perfect Daily Standup</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Stop wasting time in status meetings. Copy the exact 15-minute async standup structure we use to keep high-velocity teams in sync.
          </p>
        </header>

        <div className="bg-gray-50 rounded-3xl p-10 border border-gray-100 shadow-sm space-y-8">
          <div className="space-y-4 text-center">
            <h2 className="text-2xl font-bold">What's inside:</h2>
            <ul className="text-gray-600 space-y-2 text-left inline-block mx-auto">
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                The 3 questions that actually matter
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                Notion template for tracking blockers
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                Slack automation rules for async updates
              </li>
            </ul>
          </div>

          <div className="flex justify-center">
            <LeadCapture />
          </div>
        </div>

        <footer className="text-center space-y-4 pt-12 border-t">
          <p className="text-gray-500">
            Part of the <Link href="/accelerator-kit" className="text-black font-semibold hover:underline">Full Potential Accelerator Kit</Link>.
          </p>
          <Link href="/" className="text-sm text-gray-400 hover:text-black">
            ← Home
          </Link>
        </footer>
      </div>
    </main>
  );
}







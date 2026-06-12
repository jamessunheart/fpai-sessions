'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

export function LeadCapture() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'error'>('idle');
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setStatus('submitting');
    try {
      const res = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (res.ok) {
        router.push('/accelerator-kit?offer=magnet-unlocked');
      } else {
        setStatus('error');
      }
    } catch (err) {
      setStatus('error');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 w-full max-w-md">
      <div>
        <label htmlFor="email" className="sr-only">Email address</label>
        <input
          id="email"
          type="email"
          required
          className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-black placeholder:text-gray-500 focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
          placeholder="Enter your work email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button
        type="submit"
        disabled={status === 'submitting'}
        className="w-full rounded-xl bg-black px-4 py-3 text-base font-semibold text-white shadow-sm hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-black disabled:opacity-50"
      >
        {status === 'submitting' ? 'Unlocking...' : 'Get the Free Template'}
      </button>
      {status === 'error' && (
        <p className="text-sm text-red-600">Something went wrong. Please try again.</p>
      )}
      <p className="text-xs text-gray-500 text-center">
        We'll also send you occasional tips on engineering operations. Unsubscribe anytime.
      </p>
    </form>
  );
}







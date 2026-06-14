'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DropletsRedirect() {
  const router = useRouter();
  
  useEffect(() => {
    router.replace('/dashboard?tab=droplets');
  }, [router]);
  
  return null;
}

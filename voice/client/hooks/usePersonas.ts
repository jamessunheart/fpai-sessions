'use client';

import { useState, useEffect, useCallback } from 'react';

export interface Persona {
  name: string;
  role: string;
  personality?: string;
  speaking_style?: string;
  voice_characteristics?: string;
  language?: string;
}

export interface UsePersonasReturn {
  personas: string[];
  currentPersona: Persona | null;
  isLoading: boolean;
  error: string | null;
  loadPersona: (name: string) => Promise<void>;
  refreshPersonas: () => Promise<void>;
}

// Use production URL when not on localhost
const getApiBase = () => {
  if (typeof window === 'undefined') return 'https://localhost:8443';
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isLocal 
    ? 'https://localhost:8443'
    : 'https://fullpotential.ai/voice-api';
};
const API_BASE = getApiBase();

export function usePersonas(): UsePersonasReturn {
  const [personas, setPersonas] = useState<string[]>(['default']);
  const [currentPersona, setCurrentPersona] = useState<Persona | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCurrentPersona = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/persona`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (!data.error) {
          setCurrentPersona(data);
        }
      }
    } catch (err) {
      console.error('Failed to fetch persona:', err);
    }
  }, []);

  const refreshPersonas = useCallback(async () => {
    // For now, we only have 'default' persona
    // This could be extended to fetch from an API endpoint
    setPersonas(['default', 'assistant', 'creative', 'technical']);
    await fetchCurrentPersona();
  }, [fetchCurrentPersona]);

  const loadPersona = useCallback(async (name: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Request server to load a different persona
      const response = await fetch(`${API_BASE}/persona/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      
      if (response.ok) {
        await fetchCurrentPersona();
      } else {
        // If endpoint doesn't exist, just refresh current
        await fetchCurrentPersona();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load persona');
      // Still try to get current persona
      await fetchCurrentPersona();
    } finally {
      setIsLoading(false);
    }
  }, [fetchCurrentPersona]);

  // Initial load
  useEffect(() => {
    refreshPersonas();
  }, [refreshPersonas]);

  return {
    personas,
    currentPersona,
    isLoading,
    error,
    loadPersona,
    refreshPersonas,
  };
}


'use client';

import { useState, useCallback } from 'react';

export interface TranscriptMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  audioLevel?: number;
}

export interface UseTranscriptReturn {
  messages: TranscriptMessage[];
  addMessage: (role: 'user' | 'assistant', content: string) => void;
  updateLastMessage: (content: string) => void;
  clearTranscript: () => void;
}

export function useTranscript(): UseTranscriptReturn {
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);

  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const newMessage: TranscriptMessage = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  const updateLastMessage = useCallback((content: string) => {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const updated = [...prev];
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        content,
      };
      return updated;
    });
  }, []);

  const clearTranscript = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    addMessage,
    updateLastMessage,
    clearTranscript,
  };
}


'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

export type WebSocketStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface ServerConfig {
  sample_rate: number;
  channels: number;
  chunk_duration_ms: number;
  model_loaded: boolean;
  speech_ready?: boolean;
  persona: string | null;
}

export interface TranscriptMessage {
  role: 'user' | 'assistant';
  text: string;
  timestamp: Date;
}

export interface VoiceStatus {
  speaking: boolean;
  processing: boolean;
  responding: boolean;
  level: number;
}

export interface UseWebSocketReturn {
  status: WebSocketStatus;
  serverConfig: ServerConfig | null;
  error: string | null;
  voiceStatus: VoiceStatus;
  transcripts: TranscriptMessage[];
  connect: () => void;
  disconnect: () => void;
  sendAudio: (data: ArrayBuffer) => void;
  sendCommand: (action: string, data?: Record<string, unknown>) => void;
  clearTranscripts: () => void;
  onAudioReceived: (callback: (data: ArrayBuffer) => void) => void;
  onTranscriptReceived: (callback: (msg: TranscriptMessage) => void) => void;
}

// Compute URL at runtime inside the hook to avoid SSR issues
const LOCAL_WS_URL = 'wss://localhost:8443/ws/voice';
const PRODUCTION_WS_URL = 'wss://fullpotential.ai/voice-api/ws/voice';

function getWebSocketUrl(): string {
  if (typeof window === 'undefined') {
    return PRODUCTION_WS_URL; // SSR fallback (not actually used)
  }
  const hostname = window.location.hostname;
  return (hostname === 'localhost' || hostname === '127.0.0.1')
    ? LOCAL_WS_URL 
    : PRODUCTION_WS_URL;
}

export function useWebSocket(providedUrl?: string): UseWebSocketReturn {
  // Determine URL at runtime in the browser
  const url = providedUrl || getWebSocketUrl();
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [serverConfig, setServerConfig] = useState<ServerConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>({
    speaking: false,
    processing: false,
    responding: false,
    level: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioCallbackRef = useRef<((data: ArrayBuffer) => void) | null>(null);
  const transcriptCallbackRef = useRef<((msg: TranscriptMessage) => void) | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    setStatus('connecting');
    setError(null);

    try {
      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setStatus('connected');
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Binary audio data
          if (audioCallbackRef.current) {
            audioCallbackRef.current(event.data);
          }
        } else {
          // JSON message
          try {
            const message = JSON.parse(event.data);
            
            switch (message.type) {
              case 'config':
                setServerConfig(message.data);
                console.log('Received server config:', message.data);
                break;
                
              case 'transcript':
                const transcript: TranscriptMessage = {
                  role: message.role,
                  text: message.text,
                  timestamp: new Date(),
                };
                setTranscripts(prev => [...prev, transcript]);
                if (transcriptCallbackRef.current) {
                  transcriptCallbackRef.current(transcript);
                }
                break;
                
              case 'status':
                setVoiceStatus(prev => ({
                  ...prev,
                  speaking: message.speaking ?? prev.speaking,
                  processing: message.processing ?? prev.processing,
                  responding: message.responding ?? prev.responding,
                  level: message.level ?? prev.level,
                }));
                break;
                
              case 'cleared':
                setTranscripts([]);
                break;
                
              case 'persona_switched':
                console.log('Persona switched to:', message.name);
                break;
                
              case 'ping':
                // Keep-alive ping, no action needed
                break;
                
              case 'error':
                console.error('Server error:', message.message);
                setError(message.message || 'Server error');
                break;
                
              default:
                console.log('Unknown message type:', message.type, message);
            }
          } catch (e) {
            console.warn('Failed to parse message:', event.data);
          }
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setStatus('error');
        setError('Connection error. Make sure the server is running and SSL certificate is accepted.');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        wsRef.current = null;
        
        if (event.code !== 1000) {
          // Abnormal close, attempt reconnect
          setStatus('error');
          
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
            console.log(`Reconnecting in ${delay}ms...`);
            
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttempts.current++;
              connect();
            }, delay);
          } else {
            setError('Max reconnection attempts reached. Please check the server.');
          }
        } else {
          setStatus('disconnected');
        }
      };

    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    
    setStatus('disconnected');
    setServerConfig(null);
    reconnectAttempts.current = 0;
  }, []);

  const sendAudio = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  const sendCommand = useCallback((action: string, data?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'command',
        action,
        ...data,
      }));
    }
  }, []);

  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    sendCommand('clear');
  }, [sendCommand]);

  const onAudioReceived = useCallback((callback: (data: ArrayBuffer) => void) => {
    audioCallbackRef.current = callback;
  }, []);

  const onTranscriptReceived = useCallback((callback: (msg: TranscriptMessage) => void) => {
    transcriptCallbackRef.current = callback;
  }, []);

  return {
    status,
    serverConfig,
    error,
    voiceStatus,
    transcripts,
    connect,
    disconnect,
    sendAudio,
    sendCommand,
    clearTranscripts,
    onAudioReceived,
    onTranscriptReceived,
  };
}

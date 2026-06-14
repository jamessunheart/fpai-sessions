'use client';

import { useRef, useCallback, useState, useEffect } from 'react';

export interface UseAudioPlaybackReturn {
  isPlaying: boolean;
  volume: number;
  setVolume: (volume: number) => void;
  playAudio: (data: ArrayBuffer) => void;
  stop: () => void;
}

export function useAudioPlayback(sampleRate: number = 24000): UseAudioPlaybackReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolumeState] = useState(1.0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const queueRef = useRef<AudioBuffer[]>([]);
  const isProcessingRef = useRef(false);
  const nextPlayTimeRef = useRef(0);

  // Initialize audio context
  useEffect(() => {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    const ctx = new AudioContextClass({ sampleRate });
    audioContextRef.current = ctx;

    const gainNode = ctx.createGain();
    gainNode.gain.value = volume;
    gainNode.connect(ctx.destination);
    gainNodeRef.current = gainNode;

    return () => {
      ctx.close();
    };
  }, [sampleRate]);

  // Update volume
  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = volume;
    }
  }, [volume]);

  const setVolume = useCallback((newVolume: number) => {
    setVolumeState(Math.max(0, Math.min(1, newVolume)));
  }, []);

  const processQueue = useCallback(() => {
    if (isProcessingRef.current) return;
    if (queueRef.current.length === 0) {
      setIsPlaying(false);
      return;
    }

    const ctx = audioContextRef.current;
    const gainNode = gainNodeRef.current;
    if (!ctx || !gainNode) return;

    isProcessingRef.current = true;
    setIsPlaying(true);

    // Resume context if suspended (browser autoplay policy)
    if (ctx.state === 'suspended') {
      ctx.resume();
    }

    const buffer = queueRef.current.shift()!;
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(gainNode);

    // Schedule playback
    const currentTime = ctx.currentTime;
    const startTime = Math.max(currentTime, nextPlayTimeRef.current);
    source.start(startTime);
    nextPlayTimeRef.current = startTime + buffer.duration;

    source.onended = () => {
      isProcessingRef.current = false;
      processQueue();
    };
  }, []);

  const playAudio = useCallback((data: ArrayBuffer) => {
    const ctx = audioContextRef.current;
    if (!ctx) return;

    // Convert Int16 PCM to Float32
    const int16Data = new Int16Array(data);
    const float32Data = new Float32Array(int16Data.length);
    
    for (let i = 0; i < int16Data.length; i++) {
      float32Data[i] = int16Data[i] / 32768.0;
    }

    // Create audio buffer
    const audioBuffer = ctx.createBuffer(1, float32Data.length, sampleRate);
    audioBuffer.getChannelData(0).set(float32Data);

    // Add to queue
    queueRef.current.push(audioBuffer);
    processQueue();
  }, [sampleRate, processQueue]);

  const stop = useCallback(() => {
    queueRef.current = [];
    nextPlayTimeRef.current = 0;
    setIsPlaying(false);
  }, []);

  return {
    isPlaying,
    volume,
    setVolume,
    playAudio,
    stop,
  };
}


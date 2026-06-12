'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

export interface MicrophoneConfig {
  sampleRate?: number;
  channelCount?: number;
  echoCancellation?: boolean;
  noiseSuppression?: boolean;
  autoGainControl?: boolean;
}

export interface UseMicrophoneReturn {
  isSupported: boolean;
  isPermissionGranted: boolean;
  isRecording: boolean;
  error: string | null;
  audioLevel: number;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  onAudioData: (callback: (data: ArrayBuffer) => void) => void;
}

const DEFAULT_CONFIG: MicrophoneConfig = {
  sampleRate: 24000,
  channelCount: 1,
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
};

export function useMicrophone(config: MicrophoneConfig = {}): UseMicrophoneReturn {
  const [isSupported, setIsSupported] = useState(false);
  const [isPermissionGranted, setIsPermissionGranted] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const analyzerRef = useRef<AnalyserNode | null>(null);
  const callbackRef = useRef<((data: ArrayBuffer) => void) | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  // Check browser support
  useEffect(() => {
    const supported = !!(
      typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === 'function' &&
      (typeof window !== 'undefined' && (window.AudioContext || (window as any).webkitAudioContext))
    );
    setIsSupported(supported);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, []);

  const updateAudioLevel = useCallback(() => {
    if (analyzerRef.current && isRecording) {
      const dataArray = new Uint8Array(analyzerRef.current.frequencyBinCount);
      analyzerRef.current.getByteFrequencyData(dataArray);
      
      // Calculate RMS level
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sum / dataArray.length);
      const level = Math.min(rms / 128, 1); // Normalize to 0-1
      
      setAudioLevel(level);
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
    }
  }, [isRecording]);

  const startRecording = useCallback(async () => {
    if (!isSupported) {
      setError('Microphone not supported in this browser');
      return;
    }

    try {
      setError(null);

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: mergedConfig.sampleRate,
          channelCount: mergedConfig.channelCount,
          echoCancellation: mergedConfig.echoCancellation,
          noiseSuppression: mergedConfig.noiseSuppression,
          autoGainControl: mergedConfig.autoGainControl,
        },
      });

      setIsPermissionGranted(true);
      streamRef.current = stream;

      // Create audio context
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({
        sampleRate: mergedConfig.sampleRate,
      });
      audioContextRef.current = audioContext;

      // Create source from microphone
      const source = audioContext.createMediaStreamSource(stream);

      // Create analyzer for audio level visualization
      const analyzer = audioContext.createAnalyser();
      analyzer.fftSize = 256;
      analyzer.smoothingTimeConstant = 0.8;
      analyzerRef.current = analyzer;
      source.connect(analyzer);

      // Create script processor for raw audio data
      // Note: ScriptProcessorNode is deprecated but AudioWorklet requires more setup
      const bufferSize = 4096;
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (event) => {
        if (!callbackRef.current) return;

        const inputData = event.inputBuffer.getChannelData(0);
        
        // Convert Float32 to Int16
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        callbackRef.current(pcmData.buffer);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
      
      // Start audio level monitoring
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
      
      if (errorMessage.includes('Permission denied') || errorMessage.includes('NotAllowedError')) {
        setError('Microphone permission denied. Please allow microphone access.');
      } else if (errorMessage.includes('NotFoundError')) {
        setError('No microphone found. Please connect a microphone.');
      } else {
        setError(errorMessage);
      }
      
      console.error('Microphone error:', err);
    }
  }, [isSupported, mergedConfig, updateAudioLevel]);

  const stopRecording = useCallback(() => {
    // Stop animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Disconnect processor
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop all tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    analyzerRef.current = null;
    setIsRecording(false);
    setAudioLevel(0);
  }, []);

  const onAudioData = useCallback((callback: (data: ArrayBuffer) => void) => {
    callbackRef.current = callback;
  }, []);

  return {
    isSupported,
    isPermissionGranted,
    isRecording,
    error,
    audioLevel,
    startRecording,
    stopRecording,
    onAudioData,
  };
}


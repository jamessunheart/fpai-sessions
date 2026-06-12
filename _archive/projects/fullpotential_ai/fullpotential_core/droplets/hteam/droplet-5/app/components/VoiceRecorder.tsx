import React, { useState, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';

interface VoiceRecorderProps {
  onVoiceCommand?: (result: any) => void;
  disabled?: boolean;
  dropletContext?: {
    id: number;
    cloudId: number;
    name: string;
    provider: string;
    powerStatus: string;
    ip: string;
    region: string;
  };
  userContext?: {
    userId?: string;
    sessionId?: string;
  };
}

const VoiceRecorder: React.FC<VoiceRecorderProps> = ({ 
  onVoiceCommand, 
  disabled = false, 
  dropletContext,
  userContext 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await processVoiceCommand(audioBlob);
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setTranscript('');
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processVoiceCommand = async (audioBlob: Blob) => {
    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice-command.wav');
      
      // Add droplet context if available
      if (dropletContext) {
        formData.append('id', dropletContext.id.toString());
        formData.append('cloudId', dropletContext.cloudId.toString());
        formData.append('name', dropletContext.name);
        formData.append('provider', dropletContext.provider);
        formData.append('powerStatus', dropletContext.powerStatus);
        formData.append('ip', dropletContext.ip);
        formData.append('region', dropletContext.region);
      }
      
      // Add user context
      if (userContext) {
        formData.append('userId', userContext.userId || 'anonymous');
        formData.append('sessionId', userContext.sessionId || Date.now().toString());
      }

      const response = await fetch('http://localhost:3001/voice-command', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        setTranscript(result.transcription);
        
        // Call parent callback with result
        if (onVoiceCommand) {
          onVoiceCommand({
            transcript: result.transcription,
            command: result.command,
            result: result.result
          });
        }
      } else {
        console.error('Voice command failed:', result.error);
        setTranscript(`Error: ${result.error}`);
      }
    } catch (error) {
      console.error('Error processing voice command:', error);
      setTranscript(`Error: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClick = () => {
    if (disabled) return;
    
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="voice-recorder flex items-center gap-2">
      {/* Voice Button */}
      <button
        onClick={handleClick}
        disabled={disabled || isProcessing}
        className={`
          flex items-center justify-center w-10 h-10 rounded-full transition-all duration-200
          ${isRecording 
            ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
            : 'bg-blue-500 hover:bg-blue-600'
          }
          ${disabled || isProcessing 
            ? 'opacity-50 cursor-not-allowed' 
            : 'cursor-pointer'
          }
          text-white shadow-lg hover:shadow-xl
        `}
        title={isRecording ? 'Stop recording' : 'Start voice command'}
      >
        {isProcessing ? (
          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
        ) : isRecording ? (
          <MicOff size={16} />
        ) : (
          <Mic size={16} />
        )}
      </button>

      {/* Status Text */}
      {(isRecording || isProcessing) && (
        <div className="text-sm">
          {isRecording && (
            <span className="text-red-500 font-medium">Recording...</span>
          )}
          
          {isProcessing && (
            <span className="text-blue-500 font-medium">Processing...</span>
          )}
        </div>
      )}

      {/* Transcript Display */}
      {transcript && !isProcessing && (
        <div className="text-xs text-gray-600 max-w-xs truncate">
          "{transcript}"
        </div>
      )}
    </div>
  );
};

export default VoiceRecorder;
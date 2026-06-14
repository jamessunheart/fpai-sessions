import React, { useState, useRef } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';

const VoiceRecorder = ({ onVoiceCommand, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

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

  const processVoiceCommand = async (audioBlob) => {
    setIsProcessing(true);
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'voice-command.wav');

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
    <div className="voice-recorder">
      {/* Voice Button */}
      <button
        onClick={handleClick}
        disabled={disabled || isProcessing}
        className={`
          flex items-center justify-center w-12 h-12 rounded-full transition-all duration-200
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
          <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
        ) : isRecording ? (
          <MicOff size={20} />
        ) : (
          <Mic size={20} />
        )}
      </button>

      {/* Status Text */}
      {(isRecording || isProcessing || transcript) && (
        <div className="mt-2 text-sm">
          {isRecording && (
            <div className="text-red-500 font-medium">
              🎤 Recording... (click to stop)
            </div>
          )}
          
          {isProcessing && (
            <div className="text-blue-500 font-medium">
              🤖 Processing voice command...
            </div>
          )}
          
          {transcript && !isProcessing && (
            <div className="text-gray-700 bg-gray-100 p-2 rounded text-xs">
              <strong>You said:</strong> "{transcript}"
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VoiceRecorder;
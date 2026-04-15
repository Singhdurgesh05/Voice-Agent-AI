"use client";

import { useState, useEffect, useRef } from "react";
import { Mic, Square, Loader2 } from "lucide-react";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  isProcessing: boolean;
}

export default function AudioRecorder({ onRecordingComplete, isProcessing }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: "audio/wav" });
        onRecordingComplete(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert("Could not access microphone. Please check permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (isProcessing) {
    return (
      <button disabled className="flex items-center justify-center p-4 bg-[#0A0A0B] border border-[var(--border-primary)] opacity-50 cursor-not-allowed">
        <Loader2 className="w-5 h-5 text-[var(--accent)] animate-spin" />
      </button>
    );
  }

  return (
    <div className="relative flex items-center justify-center">
      {isRecording && (
        <div className="absolute -top-16 flex flex-col items-center p-2 bg-[#000000] border border-[var(--danger)] z-50 shadow-[0_0_15px_rgba(255,69,0,0.2)]">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-1.5 h-1.5 bg-[var(--danger)] animate-pulse-ring rounded-none" />
            <span className="text-[10px] font-mono text-[var(--danger)] font-bold tracking-widest">UPLINK</span>
            <span className="text-[10px] font-mono text-[var(--text-primary)] tracking-widest">
              {formatTime(recordingTime)}
            </span>
          </div>
          <div className="flex items-end space-x-[2px] h-4 mt-1">
            {[1, 2, 3, 5, 8, 5, 3, 2, 1].map((h, i) => (
              <div 
                key={i} 
                className="waveform-bar bg-[var(--danger)]" 
                style={{ 
                  height: `${Math.max(4, h * 2 + Math.random() * 8)}px`,
                }} 
              />
            ))}
          </div>
        </div>
      )}

      <button
        onClick={isRecording ? stopRecording : startRecording}
        className={`flex items-center justify-center p-4 transition-all duration-75 uppercase tracking-wider text-sm border ${
          isRecording 
            ? "border-[var(--danger)] bg-[var(--danger)]/10 text-[var(--danger)] shadow-[0_0_10px_rgba(255,69,0,0.2)]" 
            : "border-[var(--border-primary)] bg-[#000000] hover:bg-[#0A0A0B] text-[var(--accent)] hover:border-[var(--accent)] hover:shadow-[0_0_10px_rgba(204,255,0,0.1)]"
        }`}
      >
        {isRecording ? (
          <Square className="w-5 h-5 fill-current" />
        ) : (
          <Mic className="w-5 h-5" />
        )}
      </button>
    </div>
  );
}

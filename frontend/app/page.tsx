'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import AgentAvatar, { AgentHeadState, AgentBodyAction } from '../components/AgentAvatar';
import { useAgentState } from '../hooks/useAgentState';
import { storage } from '../lib/firebase';
import { ref, uploadString } from 'firebase/storage';
import { compareFrames } from '../utils/imageDiff';
import { calculateBrightness } from '../utils/imageProcessing';
import { useSpeechRecognition } from '../utils/speech';

const CAPTURE_INTERVAL_MS = 10000; // 10 seconds
const DIFF_THRESHOLD_PERCENT = 10;
const ANALYSIS_WIDTH = 320;

export default function Home() {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Standby");
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Avatar state (local control)
  const [avatarHeadState, setAvatarHeadState] = useState<AgentHeadState>('Idle');
  const [avatarBodyAction, setAvatarBodyAction] = useState<AgentBodyAction>('Waving');

  // New hooks
  const { isListening, transcript, startListening, stopListening, setTranscript } = useSpeechRecognition();

  // Avatar State (Debug/Demo)
  // Frontend-Backend Integration
  const { agentState } = useAgentState('default');

  const videoRef = useRef<HTMLVideoElement | null>(null); // Headless video element
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const prevFrameDataRef = useRef<ImageData | null>(null);

  // Persistent Audio Object for Mobile Compatibility
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Audio helper
  const playAudio = useCallback((base64Audio: string) => {
    try {
      // Use existing audio object if initialized (unlocked), otherwise create new
      const audio = audioRef.current || new Audio();
      if (!audioRef.current) {
        audioRef.current = audio;
      }

      const audioSrc = `data:audio/mp3;base64,${base64Audio}`;
      audio.src = audioSrc;
      audio.volume = 1.0; // Ensure volume is up

      audio.onended = () => {
        console.log("Audio ended. Resuming listening...");
        startListening();
        setStatusMessage("Listening...");
        setAvatarHeadState('Listening');
        setAvatarBodyAction('Waving');
      };

      audio.play().catch(e => {
        console.error("Audio play error", e);
        setStatusMessage("Audio Play Blocked (Tap screen)");
      });

      setStatusMessage("Speaking...");
    } catch (e) {
      console.error("Audio setup error", e);
      setStatusMessage("Audio Error");
    }
  }, [startListening]);

  // Handle Agent Interaction
  const handleAgentQuery = useCallback(async (text: string) => {
    if (!text.trim()) return;

    setStatusMessage("Thinking...");
    setAvatarHeadState('Thinking');
    setAvatarBodyAction('Idle');
    stopListening(); // Stop listening while processing

    try {
      const res = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, session_id: sessionId }),
      });

      if (!res.ok) throw new Error("Agent API failed");

      const data = await res.json();
      console.log("Agent response:", data);

      // Save session_id for future messages
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      const responseText = data.text || "";
      const audioContent = data.audio_content;

      setStatusMessage(responseText.substring(0, 20) + "...");

      if (audioContent) {
        playAudio(audioContent);
      } else {
        // If no audio, just go back to listening after a moment
        setTimeout(() => {
          startListening();
          setStatusMessage("Listening...");
          setAvatarHeadState('Listening');
          setAvatarBodyAction('Waving');
        }, 2000);
      }

    } catch (e) {
      console.error("Agent query error", e);
      setStatusMessage("Error");
      startListening(); // Resume listening on error
    }
  }, [playAudio, startListening, stopListening, sessionId]);

  // Effect: Handle Transcript (User finished speaking)
  useEffect(() => {
    if (transcript) {
      console.log("User said:", transcript);
      handleAgentQuery(transcript);
      setTranscript('');
    }
  }, [transcript, handleAgentQuery, setTranscript]);


  // Initialize Camera (Invisible Video Element)
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 1920 },
            height: { ideal: 1080 }
          }
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          // Wait for metadata to be loaded to ensure video size is known
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch(e => console.error("Play error:", e));
          };
        }

        console.log("Camera initialized (Invisible DOM Element)");
      } catch (err) {
        console.error("Camera init error:", err);
        setStatusMessage("Camera Error");
      }
    };

    startCamera();

    return () => {
      // Cleanup stream
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const processFrame = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !isMonitoring) return;

    try {
      const video = videoRef.current;
      // Check if video is actually playing and has data
      if (video.readyState < 2 || video.paused) {
        // Try to play if paused (sometimes needed on mobile wake)
        if (video.paused) video.play().catch(e => console.error("Resume error:", e));
        return;
      }

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) return;

      // Draw video frame to low-res canvas
      ctx.drawImage(video, 0, 0, ANALYSIS_WIDTH, 240);
      const currentFrameData = ctx.getImageData(0, 0, ANALYSIS_WIDTH, 240);

      // 1. Darkness Detection
      const brightness = calculateBrightness(currentFrameData);
      const DARK_THRESHOLD = 30; // Customize as needed
      if (brightness < DARK_THRESHOLD) {
        // console.log("Too dark:", brightness);
        // setStatusMessage("Dark Detected");
        // Maybe trigger a specific agent intent if persistent?
      }

      // 2. Motion/Diff Detection
      if (prevFrameDataRef.current) {
        const diff = compareFrames(prevFrameDataRef.current, currentFrameData);

        if (diff > DIFF_THRESHOLD_PERCENT) {
          console.log(`Diff ${diff.toFixed(1)}% > Threshold. Uploading...`);
          setStatusMessage(`Uploading... (${diff.toFixed(1)}%)`);

          try {
            // Create high-quality snapshot from the video element
            const uploadCanvas = document.createElement('canvas');
            uploadCanvas.width = video.videoWidth;
            uploadCanvas.height = video.videoHeight;
            const uCtx = uploadCanvas.getContext('2d');

            if (uCtx) {
              uCtx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
              const base64data = uploadCanvas.toDataURL('image/jpeg', 0.8);

              // 1. Latest
              const latestRef = ref(storage, 'latest.jpg');
              await uploadString(latestRef, base64data, 'data_url');

              // 2. History
              const nowObj = new Date();
              const YYYY = nowObj.getFullYear();
              const MM = String(nowObj.getMonth() + 1).padStart(2, '0');
              const DD = String(nowObj.getDate()).padStart(2, '0');
              const HH = String(nowObj.getHours()).padStart(2, '0');
              const mm = String(nowObj.getMinutes()).padStart(2, '0');
              const ss = String(nowObj.getSeconds()).padStart(2, '0');
              const filename = `${YYYY}${MM}${DD}_${HH}${mm}${ss}.jpg`;

              const historyRef = ref(storage, filename);
              await uploadString(historyRef, base64data, 'data_url');
              setStatusMessage("Monitoring (Uploaded)");
            }
          } catch (e) {
            console.error("Snapshot error", e);
          }

        } else {
          // console.log(`Diff ${diff.toFixed(1)}% (No upload)`);
          // setStatusMessage("Monitoring");
        }
      }

      prevFrameDataRef.current = currentFrameData;

    } catch (err) {
      console.error("Frame process error:", err);
    }
  }, [isMonitoring]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isMonitoring) {
      interval = setInterval(processFrame, CAPTURE_INTERVAL_MS);
      processFrame(); // Run immediately
    } else {
      setStatusMessage("Standby");
    }
    return () => clearInterval(interval);
  }, [isMonitoring, processFrame]);

  // Start Listening when monitoring starts? Or manual?
  // Let's make the button toggle both
  useEffect(() => {
    if (isMonitoring) {
      startListening();
      setAvatarHeadState('Listening');
      setAvatarBodyAction('Waving');
    } else {
      stopListening();
      setAvatarHeadState('Idle');
      setAvatarBodyAction('Waving');
    }
  }, [isMonitoring, startListening, stopListening]);


  return (
    <main className="h-screen w-screen relative bg-black overflow-hidden">
      {/* Invisible Video Element for Mobile Compatibility */}
      <video
        ref={videoRef}
        className="absolute top-0 left-0 w-1 h-1 opacity-0 pointer-events-none"
        playsInline
        autoPlay
        muted
      />

      {/* Hidden Canvas for processing */}
      <canvas ref={canvasRef} width={ANALYSIS_WIDTH} height={240} className="hidden" />

      {/* Avatar Display - Full Screen */}
      <div className="absolute inset-0 w-full h-full z-0">
        <AgentAvatar
          headState={avatarHeadState}
          mode="Default"
          bodyAction={avatarBodyAction}
          className="w-full h-full"
        />

        {/* Agent Message Bubble */}
        {agentState.message && (
          <div className="absolute top-8 w-full flex justify-center z-10 px-4">
            <div className="bg-white/90 text-black px-4 py-2 rounded-2xl shadow-lg max-w-xs text-center text-sm font-medium animate-bounce-in">
              {agentState.message}
            </div>
          </div>
        )}
      </div>

      {/* Floating Action Button */}
      <div className="fixed bottom-8 right-8 z-50 flex flex-col items-end gap-2">
        <div className="bg-black/60 text-white text-xs px-2 py-1 rounded backdrop-blur-sm">
          {statusMessage}
          {isListening && <span className="ml-1 text-green-400">●</span>}
        </div>
        <button
          onClick={() => {
            const nextMonitoring = !isMonitoring;

            // Unlock audio on FIRST interaction (mobile autoplay policy)
            if (nextMonitoring) {
              // Create or reuse audio object
              if (!audioRef.current) {
                audioRef.current = new Audio();
              }
              const audio = audioRef.current;

              // Play silent sound to fallback unlock
              audio.src = "data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAAYYNAAAAAAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAABhgC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7//////////////////////////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAAAAAAAAAAAAYYNAAAAAAAAAAAAAAAAAAAA";
              audio.volume = 0.01;
              audio.play().catch(e => console.log("Audio unlock failed (will retry on next event)", e));
            }

            setIsMonitoring(nextMonitoring);
          }}
          className={`w-16 h-16 rounded-full flex items-center justify-center shadow-lg transition-all transform hover:scale-105 active:scale-95 ${isMonitoring
            ? 'bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.6)] animate-pulse'
            : 'bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)]'
            }`}
        >
          {isMonitoring ? (
            // Stop Icon
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H9a1 1 0 01-1-1v-4z" />
            </svg>
          ) : (
            // Play/Camera Icon
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          )}
        </button>
      </div>
    </main>
  );
}

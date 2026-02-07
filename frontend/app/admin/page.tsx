'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { doc, setDoc } from 'firebase/firestore';
import { db, storage } from '../../lib/firebase';
import { ref, getDownloadURL } from 'firebase/storage';
import { AgentHeadState, AgentMode, AgentBodyAction } from '../../components/AgentAvatar';

export default function AdminPage() {
  const [remoteImage, setRemoteImage] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());
  const [errorCount, setErrorCount] = useState(0);

  // Simulation State
  const [simHead, setSimHead] = useState<AgentHeadState>('Thinking');
  const [simMode, setSimMode] = useState<AgentMode>('Search');
  const [simBody, setSimBody] = useState<AgentBodyAction>('Idle');
  const [simMessage, setSimMessage] = useState<string>('Target Found!');

  const sendSimulation = async () => {
    try {
      await setDoc(doc(db, 'sessions', 'default'), {
        updatedAt: Date.now(),
        headState: simHead,
        mode: simMode,
        bodyAction: simBody,
        message: simMessage,
        confidence: 0.95
      });
      alert('Sent to Firestore!');
    } catch (e) {
      console.error(e);
      alert('Error sending: ' + e);
    }
  };

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const storageRef = ref(storage, 'camera-feed/latest.jpg');
        // storageRef location must match the upload location in page.tsx
        const url = await getDownloadURL(storageRef);
        // Append timestamp to bypass browser caching
        setRemoteImage(`${url}&t=${Date.now()}`);
        setLastUpdate(Date.now());
        setErrorCount(0); // Reset error count on success
      } catch (error) {
        // console.log("Waiting for signal...", error);
        setErrorCount(prev => prev + 1);
      }
    }, 2000); // Poll every 2s

    return () => clearInterval(interval);
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-900 text-white font-sans">
      <div className="w-full max-w-6xl grid grid-cols-1 md:grid-cols-2 gap-8">

        {/* Left Col: Camera Feed */}
        <div className="flex flex-col items-center">
          <header className="w-full flex justify-between items-center mb-6 border-b border-gray-800 pb-4">
            <h1 className="text-2xl font-bold text-blue-400 tracking-tighter">Finding Agent CoCo <span className="text-gray-500 text-base font-normal">| Admin</span></h1>
            <div className="flex gap-2 text-xs">
              <span className="px-2 py-1 bg-gray-800 rounded text-gray-400">Status: {errorCount > 5 ? "OFFLINE" : "LIVE"}</span>
            </div>
          </header>

          <div className="relative w-full aspect-video bg-black rounded-xl overflow-hidden shadow-2xl border border-gray-700 flex items-center justify-center group">
            {remoteImage ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={remoteImage}
                alt="Remote Feed"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="flex flex-col items-center text-gray-500 animate-pulse">
                <svg className="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.818v6.364a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p>Waiting for CoCo Signal...</p>
              </div>
            )}

            <div className="absolute top-4 right-4 bg-red-600 text-white text-xs px-2 py-1 rounded font-bold uppercase tracking-wider shadow opacity-80">
              Live Feed
            </div>

            {/* Timestamp Overlay */}
            <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-black/80 to-transparent p-4 transform translate-y-full group-hover:translate-y-0 transition-transform">
              <p className="text-xs text-gray-300 font-mono">
                Last Received: {new Date(lastUpdate).toLocaleTimeString()}
              </p>
            </div>
          </div>

          <div className="mt-12 flex gap-6">
            <Link href="/" target="_blank" className="px-6 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors">
              Open Camera Device (New Tab)
            </Link>
          </div>
        </div>

        {/* Right Col: Simulator */}
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
          <h2 className="text-xl font-bold mb-4 text-green-400">Backend Simulator (Firestore)</h2>
          <p className="text-sm text-gray-400 mb-6">Simulate the AI Agent's response by writing to <code>sessions/default</code>.</p>

          <div className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">Head State</label>
              <select className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                value={simHead} onChange={e => setSimHead(e.target.value as any)}>
                <option value="Idle">Idle</option>
                <option value="Listening">Listening</option>
                <option value="Thinking">Thinking</option>
                <option value="Found">Found</option>
                <option value="Error">Error</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Mode</label>
              <select className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                value={simMode} onChange={e => setSimMode(e.target.value as any)}>
                <option value="Default">Default</option>
                <option value="Monitoring">Monitoring</option>
                <option value="Inference">Inference</option>
                <option value="Search">Search</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Body Action</label>
              <select className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                value={simBody} onChange={e => setSimBody(e.target.value as any)}>
                <option value="Idle">Idle</option>
                <option value="Waving">Waving</option>
                <option value="Happy">Happy</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Message</label>
              <input type="text" className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                value={simMessage} onChange={e => setSimMessage(e.target.value)} />
            </div>

            <button
              onClick={sendSimulation}
              className="w-full bg-green-600 hover:bg-green-500 text-white font-bold py-3 rounded-lg transition-all mt-4"
            >
              Update Agent State
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
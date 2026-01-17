'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { storage } from '../../lib/firebase';
import { ref, getDownloadURL } from 'firebase/storage';

export default function AdminPage() {
  const [remoteImage, setRemoteImage] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());

  useEffect(() => {
    const interval = setInterval(async () => {
        try {
            const storageRef = ref(storage, 'camera-feed/latest.jpg');
            const url = await getDownloadURL(storageRef);
            // Append timestamp to bypass browser caching of the same URL
            setRemoteImage(`${url}&t=${Date.now()}`); 
            setLastUpdate(Date.now());
        } catch (error) {
            // console.log("Waiting for signal...", error);
        }
    }, 1000); // 1s poll (Storage is slightly slower than local fs)

    return () => clearInterval(interval);
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-900 text-white">
      <h1 className="text-2xl mb-4">Admin Console (Remote View)</h1>
      <p className="text-sm text-gray-400 mb-8">Viewing camera feed from Main Device</p>

      <div className="relative border-4 border-gray-700 rounded-2xl overflow-hidden w-full max-w-2xl aspect-video bg-black flex items-center justify-center">
        {remoteImage ? (
             /* eslint-disable-next-line @next/next/no-img-element */
            <img 
                src={remoteImage} 
                alt="Remote Feed" 
                className="w-full h-full object-contain"
            />
        ) : (
            <div className="text-center p-4">
                <span className="text-4xl animate-pulse">📡</span>
                <p className="mt-2 text-gray-500">Waiting for signal...</p>
                <p className="text-xs text-gray-600 mt-1">Make sure the Main Page is open on the other device.</p>
            </div>
        )}
        
        {/* Overlay */}
        <div className="absolute top-2 right-2 bg-black/50 px-2 py-1 rounded text-xs">
            Live Feed
        </div>
      </div>

      <div className="mt-8">
         <Link href="/" className="text-blue-400 hover:text-blue-300 underline">
            &larr; Back to Main Device
         </Link>
      </div>
    </main>
  );
}
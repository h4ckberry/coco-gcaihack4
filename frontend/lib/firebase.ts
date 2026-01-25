import { initializeApp, getApps } from "firebase/app";
import { getStorage } from "firebase/storage";
import { getFirestore } from "firebase/firestore";

// TODO: Replace with your Firebase project configuration
// Get these from Firebase Console > Project Settings > General > Your Apps
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};

// Initialize Firebase (Singleton pattern)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];

if (!process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET) {
  console.error(
    "Firebase Storage Bucket is missing from environment variables! " +
    "Check your .env.local file for NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET."
  );
}

// Initialize Storage with explicit bucket URL
// This fixes the "No default bucket found" error if the default app config is missing it
const storage = getStorage(
  app,
  process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
);
const db = getFirestore(app);

export { app, storage, db };

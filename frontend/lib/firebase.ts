import { initializeApp, getApps } from "firebase/app";
import { getStorage } from "firebase/storage";
import { getFirestore } from "firebase/firestore";

// TODO: Replace with your Firebase project configuration
// Get these from Firebase Console > Project Settings > General > Your Apps
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "ai-coco.firebaseapp.com",
  projectId: "ai-coco",
  storageBucket: "ai-coco.firebasestorage.app",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

// Initialize Firebase (Singleton pattern)
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const storage = getStorage(app);
const db = getFirestore(app);

export { app, storage, db };

import { useState, useEffect } from 'react';
import { doc, onSnapshot } from 'firebase/firestore';
import { db } from '../lib/firebase';
import { AgentHeadState, AgentMode, AgentBodyAction } from '../components/AgentAvatar';

export interface AgentState {
  updatedAt?: number;
  headState: AgentHeadState;
  mode: AgentMode;
  bodyAction: AgentBodyAction;
  message?: string;
  confidence?: number;
}

const DEFAULT_STATE: AgentState = {
  headState: 'Idle',
  mode: 'Default',
  bodyAction: 'Idle',
  message: 'Standby',
};

export function useAgentState(sessionId: string = 'default') {
  const [agentState, setAgentState] = useState<AgentState>(DEFAULT_STATE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const docRef = doc(db, 'sessions', sessionId);

    // Real-time listener
    const unsubscribe = onSnapshot(
      docRef,
      (docSnap) => {
        if (docSnap.exists()) {
          const data = docSnap.data() as Partial<AgentState>;
          setAgentState((prev) => ({
            ...prev,
            ...data,
            // Ensure valid enums if backend sends partials, though usually backend sends full set
          }));
        } else {
          // Document doesn't exist yet (backend hasn't written)
          // Keep default state or handle as needed
        }
        setLoading(false);
      },
      (err) => {
        console.error("Firestore listener error:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, [sessionId]);

  return { agentState, loading, error };
}

import React, { useEffect, useRef } from 'react';

/**
 * Head State: Determines the facial expression/animation
 */
export type AgentHeadState = 'Idle' | 'Listening' | 'Thinking' | 'Found' | 'Error';

/**
 * Body Mode: Determines the body animation when in Idle state
 */
export type AgentMode = 'Monitoring' | 'Inference' | 'Search' | 'Default';

/**
 * Body Action: Overrides the mode-based body animation
 */
export type AgentBodyAction = 'Idle' | 'Waving' | 'Happy';

interface AgentAvatarProps {
  headState: AgentHeadState;
  mode: AgentMode;
  bodyAction?: AgentBodyAction;
  className?: string;
}

// Map states to file paths
const getHeadVideoPath = (state: AgentHeadState) => {
  switch (state) {
    case 'Idle': return '/assets/avatar/head_idle.mp4';
    case 'Listening': return '/assets/avatar/head_listening.mp4';
    case 'Thinking': return '/assets/avatar/head_thinking.mp4';
    case 'Found': return '/assets/avatar/head_found.mp4';
    case 'Error': return '/assets/avatar/head_error.mp4';
    default: return '/assets/avatar/head_idle.mp4';
  }
};

const getBodyVideoPath = (mode: AgentMode, action: AgentBodyAction) => {
  if (action === 'Waving') return '/assets/avatar/body_waving.mp4';
  if (action === 'Happy') return '/assets/avatar/body_happy.mp4';

  // Default action implies we look at the mode
  switch (mode) {
    case 'Monitoring': return '/assets/avatar/body_monitoring.mp4';
    case 'Inference': return '/assets/avatar/body_inference.mp4';
    case 'Search': return '/assets/avatar/body_search.mp4';
    case 'Default': return '/assets/avatar/body_idle.mp4';
    default: return '/assets/avatar/body_idle.mp4';
  }
};

export default function AgentAvatar({
  headState,
  mode,
  bodyAction = 'Idle',
  className = ''
}: AgentAvatarProps) {

  const headVideoSrc = getHeadVideoPath(headState);
  const bodyVideoSrc = getBodyVideoPath(mode, bodyAction);

  // Refs to control video playback if needed (e.g. to ensure sync or loop)
  const headRef = useRef<HTMLVideoElement>(null);
  const bodyRef = useRef<HTMLVideoElement>(null);

  // Effect to ensure videos play when source changes
  useEffect(() => {
    if (headRef.current) {
      headRef.current.load();
      headRef.current.play().catch(() => { }); // catch autoplay policy blocks
    }
  }, [headVideoSrc]);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.load();
      bodyRef.current.play().catch(() => { });
    }
  }, [bodyVideoSrc]);

  return (
    <div className={`flex flex-col w-full h-full overflow-hidden ${className}`}>
      {/* Head Layer - Top Section (approx 40%) */}
      {/* using object-cover to fill width, object-bottom to keep neck visible */}
      <div className="relative w-full h-[40%] shrink-0 flex items-end justify-center">
        <video
          ref={headRef}
          src={headVideoSrc}
          className="w-full h-full object-cover object-bottom pointer-events-none"
          autoPlay
          loop
          muted
          playsInline
        />
      </div>

      {/* Body Layer - Bottom Section (approx 60%) */}
      {/* using object-cover to fill width, object-top to keep neck visible */}
      <div className="relative w-full h-[60%] shrink-0 flex items-start justify-center">
        <video
          ref={bodyRef}
          src={bodyVideoSrc}
          className="w-full h-full object-cover object-top pointer-events-none"
          autoPlay
          loop
          muted
          playsInline
        />
      </div>
    </div>
  );
}

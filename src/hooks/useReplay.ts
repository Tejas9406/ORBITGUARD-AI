import { useState, useEffect, useRef, useCallback } from 'react';
import { DEMO_REPLAY_FRAMES } from '../data/demoHealth';
import type { ReplayFrame } from '../types/mission';

export type PlaybackSpeed = 1 | 2 | 5;

export function useReplay() {
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);
  const timerRef = useRef<number | null>(null);

  const totalFrames = DEMO_REPLAY_FRAMES.length;
  const currentFrame: ReplayFrame = DEMO_REPLAY_FRAMES[currentFrameIndex] || DEMO_REPLAY_FRAMES[0];

  const framesHistory: ReplayFrame[] = DEMO_REPLAY_FRAMES.slice(0, currentFrameIndex + 1);

  const handleNext = useCallback(() => {
    setCurrentFrameIndex((prev) => {
      if (prev >= totalFrames - 1) {
        setIsPlaying(false);
        return prev;
      }
      return prev + 1;
    });
  }, [totalFrames]);

  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(150, 1000 / speed);
      timerRef.current = window.setInterval(handleNext, intervalMs);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPlaying, speed, handleNext]);

  const play = () => {
    if (currentFrameIndex >= totalFrames - 1) {
      setCurrentFrameIndex(0);
    }
    setIsPlaying(true);
  };

  const pause = () => {
    setIsPlaying(false);
  };

  const restart = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(0);
  };

  const seek = (index: number) => {
    const clamped = Math.max(0, Math.min(totalFrames - 1, index));
    setCurrentFrameIndex(clamped);
  };

  const changeSpeed = (newSpeed: PlaybackSpeed) => {
    setSpeed(newSpeed);
  };

  const stepForward = () => {
    setIsPlaying(false);
    setCurrentFrameIndex((prev) => Math.min(totalFrames - 1, prev + 1));
  };

  const stepBackward = () => {
    setIsPlaying(false);
    setCurrentFrameIndex((prev) => Math.max(0, prev - 1));
  };

  return {
    currentFrame,
    currentFrameIndex,
    totalFrames,
    isPlaying,
    speed,
    framesHistory,
    play,
    pause,
    restart,
    seek,
    changeSpeed,
    stepForward,
    stepBackward,
  };
}

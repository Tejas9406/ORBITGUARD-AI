import React from 'react';
import { EarthEnvironmentScene } from '../space/EarthEnvironmentScene';

interface LandingEarthSceneProps {
  className?: string;
  onSelectSatellite?: (satId: string) => void;
}

export const LandingEarthScene: React.FC<LandingEarthSceneProps> = ({ className = '', onSelectSatellite }) => {
  return (
    <div className={`relative w-full h-full ${className}`}>
      <EarthEnvironmentScene
        mode="cinematic"
        height={window.innerHeight || 800}
        showUIOverlay={false}
        onSelectSatellite={(sat) => {
          if (onSelectSatellite) onSelectSatellite(sat.id);
        }}
      />
    </div>
  );
};

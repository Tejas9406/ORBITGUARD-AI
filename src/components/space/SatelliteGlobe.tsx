import React from 'react';
import type { SatelliteStatus, SatelliteMetadata } from '../../types/satellite';
import { EarthEnvironmentScene } from './EarthEnvironmentScene';

interface SatelliteGlobeProps {
  status?: SatelliteStatus;
  healthScore?: number;
  activeAnomaliesCount?: number;
  height?: number;
  className?: string;
  selectedSatelliteId?: string;
  onNavigateTelemetry?: () => void;
  onNavigateAnomaly?: () => void;
  onSelectSatellite?: (sat: SatelliteMetadata) => void;
}

export const SatelliteGlobe: React.FC<SatelliteGlobeProps> = ({
  status: _status,
  healthScore: _healthScore,
  activeAnomaliesCount: _activeAnomaliesCount,
  height = 480,
  className = '',
  selectedSatelliteId,
  onNavigateTelemetry: _onNavigateTelemetry,
  onNavigateAnomaly: _onNavigateAnomaly,
  onSelectSatellite,
}) => {
  return (
    <EarthEnvironmentScene
      mode="dashboard"
      height={height}
      className={className}
      selectedSatelliteId={selectedSatelliteId}
      showUIOverlay={true}
      onSelectSatellite={onSelectSatellite}
    />
  );
};

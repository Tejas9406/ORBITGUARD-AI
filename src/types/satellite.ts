export type SatelliteStatus = 'NOMINAL' | 'WARNING' | 'CRITICAL';

export interface SatellitePosition {
  latitude: number;
  longitude: number;
  altitudeKm: number;
  timestamp: string;
  velocityKmS?: number;
}

export interface OrbitPoint {
  latitude: number;
  longitude: number;
  altitudeKm: number;
}

export interface GroundStation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  elevationM: number;
}

export interface SatelliteMetadata {
  id: string;
  noradId: string;
  name: string;
  operator: string;
  operatingCountry: string; // The country that operates the spacecraft
  currentSubpoint: {
    lat: number;
    lon: number;
    geographicRegion: string; // The geographic location currently beneath its ground track
  };
  missionType: string;
  orbitType: string;
  altitudeKm: number;
  inclinationDeg: number;
  status: SatelliteStatus;
  subsystems: {
    eps: 'NOMINAL' | 'WARNING' | 'CRITICAL';
    tcs: 'NOMINAL' | 'WARNING' | 'CRITICAL';
    aocs: 'NOMINAL' | 'WARNING' | 'CRITICAL';
    ttc: 'NOMINAL' | 'WARNING' | 'CRITICAL';
    obc: 'NOMINAL' | 'WARNING' | 'CRITICAL';
    sensors: 'NOMINAL' | 'WARNING' | 'CRITICAL';
  };
  telemetryChannels: string[];
  activeAnomaliesCount: number;
  launchDate: string;
  dataFreshness: string;
  dataSource: 'LIVE_BACKEND_STREAM' | 'SIMULATED_KEPLERIAN_PROPAGATION';
  isSimulatedOrbit: boolean;
}


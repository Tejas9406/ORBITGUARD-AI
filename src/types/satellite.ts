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

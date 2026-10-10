import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import type { OverallHealthMetrics, SubsystemHealth } from '../types/health';
import type { SystemStatusState } from '../types/mission';

export function useHealth() {
  const [overallHealth, setOverallHealth] = useState<OverallHealthMetrics | null>(null);
  const [subsystems, setSubsystems] = useState<SubsystemHealth[]>([]);
  const [selectedSubsystemId, setSelectedSubsystemId] = useState<string>('power');
  const [systemStatus, setSystemStatus] = useState<SystemStatusState | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(() => {
    let isCancelled = false;
    setIsLoading(true);
    apiService.checkBackendHealth().then(() => {
      if (!isCancelled) {
        // Health is evidence-derived per analysis run. Do not display a
        // fabricated fleet score before a run is available.
        setOverallHealth(null);
        setSubsystems([]);
        setSystemStatus(null);
      }
    }).catch((err: unknown) => {
      if (!isCancelled) setError(err instanceof Error ? err.message : 'Failed to load health metrics');
    }).finally(() => {
      if (!isCancelled) setIsLoading(false);
    });
    return () => { isCancelled = true; };
  }, []);

  useEffect(() => {
    const cancel = loadHealth();
    return cancel;
  }, [loadHealth]);

  const selectedSubsystem = subsystems.find((s) => s.id === selectedSubsystemId) || subsystems[0];

  return {
    overallHealth,
    subsystems,
    selectedSubsystem,
    selectedSubsystemId,
    setSelectedSubsystemId,
    systemStatus,
    isLoading,
    error,
    reload: loadHealth,
  };
}

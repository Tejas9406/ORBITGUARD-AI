import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { DEMO_OVERALL_HEALTH, DEMO_SUBSYSTEMS, DEMO_SYSTEM_STATUS } from '../data/demoHealth';
import type { OverallHealthMetrics, SubsystemHealth } from '../types/health';
import type { SystemStatusState } from '../types/mission';

export function useHealth() {
  const [overallHealth, setOverallHealth] = useState<OverallHealthMetrics | null>(DEMO_OVERALL_HEALTH);
  const [subsystems, setSubsystems] = useState<SubsystemHealth[]>(DEMO_SUBSYSTEMS);
  const [selectedSubsystemId, setSelectedSubsystemId] = useState<string>('power');
  const [systemStatus, setSystemStatus] = useState<SystemStatusState | null>(DEMO_SYSTEM_STATUS);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(() => {
    let isCancelled = false;
    setIsLoading(true);
    Promise.all([
      apiService.getOverallHealth(),
      apiService.getSubsystemHealth(),
      apiService.getSystemStatus(),
    ]).then(([overall, subs, sys]) => {
      if (!isCancelled) {
        setOverallHealth(overall);
        setSubsystems(subs);
        setSystemStatus(sys);
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

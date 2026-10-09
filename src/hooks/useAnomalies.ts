import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { DEMO_ANOMALIES } from '../data/demoAnomalies';
import type { AnomalyEvent, AnomalySeverity, AnomalyStatus } from '../types/anomaly';

export function useAnomalies(initialAnomalyId?: string) {
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>(DEMO_ANOMALIES);
  const [selectedAnomalyId, setSelectedAnomalyId] = useState<string>(initialAnomalyId || 'ANM-0047');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [severityFilter, setSeverityFilter] = useState<AnomalySeverity | 'ALL'>('ALL');
  const [statusFilter, setStatusFilter] = useState<AnomalyStatus | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadAnomalies = useCallback(() => {
    let isCancelled = false;
    setIsLoading(true);
    apiService.getAnomalies().then((data) => {
      if (!isCancelled) setAnomalies(data);
    }).catch((err: unknown) => {
      if (!isCancelled) setError(err instanceof Error ? err.message : 'Failed to load anomalies');
    }).finally(() => {
      if (!isCancelled) setIsLoading(false);
    });
    return () => { isCancelled = true; };
  }, []);

  useEffect(() => {
    const cancel = loadAnomalies();
    return cancel;
  }, [loadAnomalies]);

  const filteredAnomalies = anomalies.filter((a) => {
    if (severityFilter !== 'ALL' && a.severity !== severityFilter) return false;
    if (statusFilter !== 'ALL' && a.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match =
        a.id.toLowerCase().includes(q) ||
        a.channelId.toLowerCase().includes(q) ||
        a.channelName.toLowerCase().includes(q) ||
        a.subsystem.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const selectedAnomaly =
    anomalies.find((a) => a.id === selectedAnomalyId) || anomalies[0] || null;

  return {
    anomalies: filteredAnomalies,
    allAnomalies: anomalies,
    selectedAnomaly,
    selectedAnomalyId,
    setSelectedAnomalyId,
    severityFilter,
    setSeverityFilter,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
    isLoading,
    error,
    reload: loadAnomalies,
  };
}

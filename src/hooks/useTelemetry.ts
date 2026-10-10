import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import type { TelemetryChannel, TelemetryPoint, TelemetryStreamFilter } from '../types/telemetry';

export function useTelemetry(initialChannelId: string = '') {
  const [channels, setChannels] = useState<TelemetryChannel[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>(initialChannelId);
  const [series, setSeries] = useState<TelemetryPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TelemetryStreamFilter>({
    channelId: initialChannelId,
    timeRange: '1H',
    anomalyOnly: false,
    severityFilter: 'ALL',
    searchQuery: '',
  });

  const loadData = useCallback((chanId: string) => {
    let isCancelled = false;
    setIsLoading(true);
    apiService.getChannels().then(async (chList) => {
      const requestedChanExists = chList.some(c => c.id === chanId);
      const active = (chanId && requestedChanExists) ? chanId : (chList[0]?.id);
      if (!active) throw new Error('The selected dataset contains no channels.');
      const serList = await apiService.getTelemetrySeries(active);
      if (!isCancelled) {
        const values = serList.map((p) => p.value);
        const mean = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
        const stdDev = values.length ? Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length) : 0;
        const anomPoints = serList.filter((p) => p.isAnomaly);
        const anomCount = anomPoints.length;
        const maxZ = (values.length && stdDev > 0) ? Math.max(...values.map(v => Math.abs((v - mean) / stdDev))) : 0;
        const dynamicScore = Math.min(1.0, maxZ / 5.0);

        setChannels(chList.map((item) => {
          if (item.id === active) {
            return {
              ...item,
              currentValue: Number((values.at(-1) ?? item.currentValue ?? 0).toFixed(4)),
              baselineValue: Number(mean.toFixed(4)),
              mean: Number(mean.toFixed(4)),
              stdDev: Number(stdDev.toFixed(4)),
              min: Number((values.length ? Math.min(...values) : (item.min ?? 0)).toFixed(4)),
              max: Number((values.length ? Math.max(...values) : (item.max ?? 0)).toFixed(4)),
              recentAnomalyCount: anomCount > 0 ? anomCount : item.recentAnomalyCount,
              anomalyScore: item.anomalyScore > 0 ? item.anomalyScore : Number(dynamicScore.toFixed(2)),
              status: (anomCount > 0 || item.recentAnomalyCount > 0) ? 'CRITICAL' : 'NOMINAL',
            };
          }
          return item;
        }));
        setSeries(serList);
        setSelectedChannelId(prev => prev || active);
      }

    }).catch((err: unknown) => {
      if (!isCancelled) setError(err instanceof Error ? err.message : 'Failed to load telemetry stream');
    }).finally(() => {
      if (!isCancelled) setIsLoading(false);
    });
    return () => { isCancelled = true; };
  }, []); // no dependency on selectedChannelId

  useEffect(() => {
    const cancel = loadData(selectedChannelId);
    return cancel;
  }, [selectedChannelId, loadData]);

  const selectChannel = (channelId: string) => {
    setSelectedChannelId(channelId);
    setFilter((prev) => ({ ...prev, channelId }));
  };

  const selectedChannel = channels.find((c) => c.id === selectedChannelId) || channels[0];

  return {
    channels,
    selectedChannel,
    selectedChannelId,
    series,
    isLoading,
    error,
    filter,
    setFilter,
    selectChannel,
    reload: () => loadData(selectedChannelId),
  };
}

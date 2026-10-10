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
      const active = chanId || chList[0]?.id;
      if (!active) throw new Error('The selected dataset contains no channels.');
      const serList = await apiService.getTelemetrySeries(active);
      if (!isCancelled) {
        const values = serList.map((p) => p.value);
        const mean = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
        const stdDev = values.length ? Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length) : 0;
        setChannels(chList.map((item) => item.id === active ? { ...item, currentValue: values.at(-1) ?? NaN, baselineValue: mean, mean, stdDev, min: values.length ? Math.min(...values) : 0, max: values.length ? Math.max(...values) : 0 } : item));
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

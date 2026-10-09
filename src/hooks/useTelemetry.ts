import { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api';
import { DEMO_CHANNELS, generateDemoTelemetrySeries } from '../data/demoTelemetry';
import type { TelemetryChannel, TelemetryPoint, TelemetryStreamFilter } from '../types/telemetry';

export function useTelemetry(initialChannelId: string = 'Channel_04') {
  const [channels, setChannels] = useState<TelemetryChannel[]>(DEMO_CHANNELS);
  const [selectedChannelId, setSelectedChannelId] = useState<string>(initialChannelId);
  const [series, setSeries] = useState<TelemetryPoint[]>(() => generateDemoTelemetrySeries(initialChannelId));
  const [isLoading, setIsLoading] = useState<boolean>(false);
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
    Promise.all([
      apiService.getChannels(),
      apiService.getTelemetrySeries(chanId),
    ]).then(([chList, serList]) => {
      if (!isCancelled) {
        setChannels(chList);
        setSeries(serList);
      }
    }).catch((err: unknown) => {
      if (!isCancelled) setError(err instanceof Error ? err.message : 'Failed to load telemetry stream');
    }).finally(() => {
      if (!isCancelled) setIsLoading(false);
    });
    return () => { isCancelled = true; };
  }, []);

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

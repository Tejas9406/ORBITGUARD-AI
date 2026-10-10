import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';
import { tokens } from '../../styles/tokens';

export interface PlotlyChartProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  config?: Partial<Plotly.Config>;
  style?: React.CSSProperties;
  className?: string;
  onHover?: (event: Plotly.PlotMouseEvent) => void;
  onUnhover?: (event: Plotly.PlotMouseEvent) => void;
  onClick?: (event: Plotly.PlotMouseEvent) => void;
}

export const PlotlyChartWrapper: React.FC<PlotlyChartProps> = ({
  data,
  layout = {},
  config = {},
  style = { width: '100%', height: '100%' },
  className = '',
  onHover,
  onUnhover,
  onClick,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Aerospace default dark theme layout
    const defaultLayout: Partial<Plotly.Layout> = {
      paper_bgcolor: tokens.chartTheme.paperBg,
      plot_bgcolor: tokens.chartTheme.plotBg,
      font: {
        family: 'Kineks, sans-serif',
        size: 11,
        color: tokens.chartTheme.fontColor,
      },
      margin: { l: 50, r: 25, t: 35, b: 40 },
      autosize: true,
      hovermode: 'closest',
      hoverlabel: {
        bgcolor: '#15213B',
        bordercolor: '#00E5FF',
        font: {
          family: 'JetBrains Mono, Kineks, monospace',
          size: 11,
          color: '#F1F5F9',
        },
      },
      xaxis: {
        gridcolor: tokens.chartTheme.gridColor,
        zerolinecolor: tokens.chartTheme.zeroLineColor,
        tickfont: { color: tokens.colors.textSecondary, size: 10, family: 'JetBrains Mono, Kineks, monospace' },
        showgrid: true,
        gridwidth: 1,
      },
      yaxis: {
        gridcolor: tokens.chartTheme.gridColor,
        zerolinecolor: tokens.chartTheme.zeroLineColor,
        tickfont: { color: tokens.colors.textSecondary, size: 10, family: 'JetBrains Mono, Kineks, monospace' },
        showgrid: true,
        gridwidth: 1,
      },
      legend: {
        orientation: 'h',
        x: 0,
        y: 1.12,
        font: { size: 11, color: '#CBD5E1' },
        bgcolor: 'transparent',
      },
      ...layout,
    };

    const defaultConfig: Partial<Plotly.Config> = {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: [
        'lasso2d',
        'select2d',
        'toggleSpikelines',
        'hoverClosestCartesian',
        'hoverCompareCartesian',
      ],
      toImageButtonOptions: {
        format: 'png',
        filename: 'satshield_telemetry_export',
        height: 600,
        width: 1000,
        scale: 2,
      },
      ...config,
    };

    const node = containerRef.current;

    Plotly.react(node, data, defaultLayout, defaultConfig);

    // Event listeners
    if (onHover) {
      (node as any).on('plotly_hover', onHover);
    }
    if (onUnhover) {
      (node as any).on('plotly_unhover', onUnhover);
    }
    if (onClick) {
      (node as any).on('plotly_click', onClick);
    }

    // Resize observer for responsive layout changes
    const resizeObserver = new ResizeObserver(() => {
      if (node && node.offsetParent !== null && node.clientWidth > 0 && node.clientHeight > 0) {
        try {
          Plotly.Plots.resize(node);
        } catch {
          // Gracefully suppress resize during DOM detachment
        }
      }
    });
    resizeObserver.observe(node);

    return () => {
      resizeObserver.disconnect();
      if (node) {
        Plotly.purge(node);
      }
    };
  }, [data, layout, config, onHover, onUnhover, onClick]);

  return <div ref={containerRef} style={style} className={className} />;
};

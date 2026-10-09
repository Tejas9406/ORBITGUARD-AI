/**
 * SATSHIELD Design Tokens
 * Centralized aerospace mission-control design system tokens.
 * TECH-BLUE + BLACK + GLASS + AEROSPACE MISSION CONTROL
 * Used across React components and Plotly visualization theming.
 */

export const tokens = {
  colors: {
    // Base Aerospace Backgrounds (Near-black, Deep Navy, Dark Blue)
    background: '#050811', // Near-black base
    backgroundAlt: '#080E1A',
    backgroundOverlay: 'rgba(5, 8, 17, 0.85)',
    
    // Glass Surface Tokens (Dark blue with transparency & blur)
    surface: 'rgba(11, 19, 36, 0.82)', 
    surfaceSolid: '#0B1324',
    surfaceElevated: 'rgba(17, 28, 52, 0.85)',
    surfaceElevatedHover: 'rgba(23, 38, 70, 0.95)',
    surfaceOverlay: 'rgba(7, 12, 24, 0.75)',

    // Cool Technical Borders
    border: '#15243F', // Cool-blue subdued border
    borderLight: '#1E355B',
    borderGlass: 'rgba(56, 189, 248, 0.16)', // Subtle cyan glass edge
    borderAccent: 'rgba(0, 229, 255, 0.35)', // Cyan accent border
    borderAccentStrong: '#00E5FF',
    borderCritical: 'rgba(239, 68, 68, 0.55)',
    borderWarning: 'rgba(245, 158, 11, 0.5)',
    borderSuccess: 'rgba(16, 185, 129, 0.45)',

    // Typography
    textPrimary: '#F8FAFC', // Crisp near-white
    textSecondary: '#94A3B8', // Technical slate
    textMuted: '#64748B', // Subdued labels
    textInverse: '#050811',

    // Primary Technical Accents
    accent: '#00E5FF', // Technical Cyan
    accentElectric: '#00D2EE', // Electric Blue
    accentHover: '#33EBFF',
    accentMuted: 'rgba(0, 229, 255, 0.12)',
    accentGlow: 'rgba(0, 229, 255, 0.25)',
    accentDark: '#0369A1',

    // Status / Severity Tokens
    healthy: '#10B981', // Teal / Green
    healthyBg: 'rgba(16, 185, 129, 0.12)',
    healthyBorder: 'rgba(16, 185, 129, 0.35)',

    warning: '#F59E0B', // Amber
    warningBg: 'rgba(245, 158, 11, 0.14)',
    warningBorder: 'rgba(245, 158, 11, 0.4)',

    critical: '#EF4444', // Red / Coral
    criticalBg: 'rgba(239, 68, 68, 0.16)',
    criticalBorder: 'rgba(239, 68, 68, 0.5)',

    info: '#38BDF8', // Technical Sky Blue
    infoBg: 'rgba(56, 189, 248, 0.12)',
    infoBorder: 'rgba(56, 189, 248, 0.32)',

    analytics: '#A855F7', // Subtle Violet for secondary machine learning metrics
    analyticsBg: 'rgba(168, 85, 247, 0.12)',
    analyticsBorder: 'rgba(168, 85, 247, 0.35)',
  },

  typography: {
    fontSans: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontDisplay: '"Space Grotesk", "Inter", sans-serif',
  },

  radii: {
    xs: '2px',
    sm: '4px',
    md: '6px',
    lg: '8px',
    xl: '10px',
    full: '9999px',
  },

  shadows: {
    panel: '0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 0 1px 1px rgba(21, 36, 63, 0.5)',
    glass: '0 8px 32px 0 rgba(0, 0, 0, 0.45), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
    glowCyan: '0 0 15px -3px rgba(0, 229, 255, 0.25)',
    glowRed: '0 0 15px -3px rgba(239, 68, 68, 0.35)',
    glowAmber: '0 0 15px -3px rgba(245, 158, 11, 0.25)',
  },

  // Centralized Plotly Chart Layout Tokens
  chartTheme: {
    paperBg: '#0B1324',
    plotBg: '#060B14',
    fontColor: '#94A3B8',
    gridColor: '#13213A',
    zeroLineColor: '#1D3256',
    telemetryLine: '#00E5FF', // Cyan actual
    baselineLine: '#64748B', // Dim slate expected
    thresholdLine: '#F59E0B', // Amber threshold
    anomalyMarker: '#EF4444', // Red anomaly
    anomalyFill: 'rgba(239, 68, 68, 0.18)',
    secondaryLine: '#A855F7', // Violet
    tertiaryLine: '#10B981', // Green
  },
} as const;

export type DesignTokens = typeof tokens;

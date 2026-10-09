import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { DashboardPage } from './pages/DashboardPage';
import { TelemetryExplorerPage } from './pages/TelemetryExplorerPage';
import { AnomalyAnalysisPage } from './pages/AnomalyAnalysisPage';
import { SubsystemHealthPage } from './pages/SubsystemHealthPage';
import { TelemetryReplayPage } from './pages/TelemetryReplayPage';
import { MissionHistoryPage } from './pages/MissionHistoryPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="telemetry" element={<TelemetryExplorerPage />} />
          <Route path="anomalies" element={<AnomalyAnalysisPage />} />
          <Route path="health" element={<SubsystemHealthPage />} />
          <Route path="replay" element={<TelemetryReplayPage />} />
          <Route path="history" element={<MissionHistoryPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

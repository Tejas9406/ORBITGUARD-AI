import React,{useEffect,useState} from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/layout/PageHeader';
import { apiService } from '../services/api';

export const MissionHistoryPage:React.FC = () => {
    const [runs, setRuns] = useState<Awaited<ReturnType<typeof apiService.getHistory>>>([]);
    const [error, setError] = useState('');
    const navigate = useNavigate();
    
    const reload = () => {
        apiService.getHistory().then(setRuns).catch(e => setError(e.message));
    };
    
    useEffect(() => { reload(); }, []);
    
    return (
        <div className="space-y-6">
            <PageHeader title="Analysis history" subtitle="Runs retained by the current backend session." badge="SESSION HISTORY" />
            <div className="sat-panel p-5">
                {error && <p className="text-rose-300">{error}</p>}
                {!error && !runs.length && <p className="text-slate-400">No runs recorded. Run an analysis from Telemetry Explorer.</p>}
                {runs.map(run => (
                    <div key={run.run_id} className="flex flex-wrap gap-4 items-center justify-between border-b border-[#1E2D4A] py-4 font-mono text-xs">
                        <div>
                            <b className="text-cyan-300">{run.run_id}</b>
                            <p className="mt-1 text-slate-400">{run.dataset_id} • {run.channel_id} • {run.duration_seconds}s</p>
                        </div>
                        <div className="text-slate-200">{run.event_count} consensus events</div>
                        <button onClick={() => navigate('/anomalies')} className="rounded border border-cyan-500/40 px-3 py-1.5 text-cyan-300">VIEW EVENTS</button>
                    </div>
                ))}
            </div>
        </div>
    );
};

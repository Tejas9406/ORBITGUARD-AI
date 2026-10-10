import React, { useEffect, useState } from 'react';
import { Menu, Database, Clock } from 'lucide-react';
import { apiService } from '../../services/api';

interface Props { onOpenMobileMenu: () => void; isAttentionRequired?: boolean }
export const TopBar: React.FC<Props> = ({ onOpenMobileMenu }) => {
  const [time, setTime] = useState(() => new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC');
  const [datasets, setDatasets] = useState<{id:string, source:string}[]>([]);
  const [current, setCurrent] = useState<string>('');

  useEffect(() => {
    const id = window.setInterval(() => setTime(new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'), 1000);
    apiService.getDatasets().then(ds => {
        setDatasets(ds);
        if (apiService.getCurrentDataset()) {
            setCurrent(apiService.getCurrentDataset()!);
        } else if (ds.length > 0) {
            setCurrent(ds[0].id);
        }
    });
    return () => clearInterval(id); 
  }, []);

  const handleDatasetChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value;
    setCurrent(id);
    await apiService.setDataset(id);
    window.location.reload(); // Quick dirty way to refresh all components to use new dataset
  };

  return <header className="h-16 bg-[#090E1B] border-b border-[#1E2D4A] px-4 md:px-6 flex items-center justify-between sticky top-0 z-30">
    <div className="flex items-center gap-3"><button onClick={onOpenMobileMenu} className="lg:hidden p-2 text-slate-300" aria-label="Open navigation"><Menu className="w-5 h-5"/></button><div><p className="font-mono text-sm font-bold text-slate-100">ORBIT<span className="text-cyan-400">GUARD</span></p><p className="text-[10px] font-mono text-slate-400">Telemetry analysis workspace</p></div></div>
    <div className="flex items-center gap-3 text-xs font-mono">
        <span className="hidden sm:flex items-center gap-1.5 text-cyan-300"><Database className="w-3.5 h-3.5"/>
            <select className="bg-[#080E1C] border border-[#1E2D4A] text-cyan-300 rounded focus:outline-none ml-1 px-1 py-0.5" value={current} onChange={handleDatasetChange}>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.source}</option>)}
            </select>
        </span>
        <span className="hidden md:flex items-center gap-1.5 text-slate-400"><Clock className="w-3.5 h-3.5"/>{time}</span>
    </div>
  </header>;
};

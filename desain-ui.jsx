import React, { useState, useEffect, useRef } from 'react';
import { 
  FileSpreadsheet, 
  Settings, 
  Play, 
  RotateCcw, 
  FolderOpen, 
  FileText,
  CheckCircle2, 
  AlertCircle, 
  UploadCloud, 
  Terminal,
  X,
  Plus,
  Trash2,
  ExternalLink,
  ChevronRight,
  ArrowRight
} from 'lucide-react';

const App = () => {
  // State Utama
  const [appState, setAppState] = useState('idle'); // idle, checking, ready, running, success, failed
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [sourceFile, setSourceFile] = useState(null);
  const [selectedJob, setSelectedJob] = useState('job-01');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([
    { type: 'info', msg: 'Sistem siap. Silakan pilih file sumber.', time: '10:00:00' }
  ]);
  const [preflightStatus, setPreflightStatus] = useState(null);

  const logEndRef = useRef(null);

  // Auto-scroll untuk log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Handler Aksi
  const addLog = (type, msg) => {
    const time = new Date().toLocaleTimeString('id-ID', { hour12: false });
    setLogs(prev => [...prev, { type, msg, time }]);
  };

  const handleFileSelect = () => {
    // Simulasi pemilihan file
    const file = "data_transaksi_maret_2024.csv";
    setSourceFile(file);
    addLog('info', `File sumber terpilih: ${file}`);
    runPreflight();
  };

  const runPreflight = () => {
    setAppState('checking');
    addLog('info', 'Menjalankan pemeriksaan preflight otomatis...');
    
    setTimeout(() => {
      setPreflightStatus({
        status: 'success',
        message: 'Validasi sukses. 1.250 baris terdeteksi.'
      });
      setAppState('ready');
      addLog('info', 'Preflight sukses. Konfigurasi dan file master tersedia.');
    }, 1000);
  };

  const handleExecute = () => {
    setAppState('running');
    setProgress(0);
    addLog('info', 'Memulai proses transformasi...');
    
    const steps = [
      'Memuat konfigurasi', 'Menyiapkan buffer', 'Membaca file sumber', 
      'Lookup data master', 'Melakukan transformasi data', 'Menyusun output Excel', 
      'Menulis file ke disk'
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        addLog('info', `Langkah ${currentStep + 1}/${steps.length}: ${steps[currentStep]}`);
        setProgress(((currentStep + 1) / steps.length) * 100);
        currentStep++;
      } else {
        clearInterval(interval);
        setAppState('success');
        addLog('success', 'Transformasi selesai! File siap dibuka.');
      }
    }, 600);
  };

  const handleReset = () => {
    setAppState('idle');
    setSourceFile(null);
    setPreflightStatus(null);
    setProgress(0);
    addLog('info', 'Sesi direset. Siap untuk file baru.');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans flex flex-col">
      
      {/* Header Bar */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center gap-4">
          <div className="bg-indigo-600 p-2.5 rounded-xl shadow-lg shadow-indigo-100 text-white">
            <FileSpreadsheet size={24} />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-800">X-Form <span className="text-indigo-600">Engine</span></h1>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Automation Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-all shadow-sm"
          >
            <Settings size={18} />
            <span>Pengaturan Job</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-8 space-y-6 overflow-y-auto">
        
        {/* Step Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Card 1: Input */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <span className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-tighter">
                <span className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center">1</span>
                Source File
              </span>
              {sourceFile && <CheckCircle2 size={16} className="text-emerald-500" />}
            </div>
            
            <div className="flex-1 flex flex-col justify-center">
              {!sourceFile ? (
                <button 
                  onClick={handleFileSelect}
                  className="group border-2 border-dashed border-slate-200 rounded-xl p-8 hover:border-indigo-400 hover:bg-indigo-50/50 transition-all text-center"
                >
                  <UploadCloud className="mx-auto mb-3 text-slate-300 group-hover:text-indigo-400 transition-colors" size={40} />
                  <p className="text-sm font-bold text-slate-700">Pilih atau Drag File</p>
                  <p className="text-xs text-slate-400 mt-1">Excel atau CSV (.xlsx, .csv)</p>
                </button>
              ) : (
                <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-100 text-emerald-600 rounded-lg">
                      <FileText size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold truncate">{sourceFile}</p>
                      <p className="text-[10px] text-slate-400">Terdeteksi: CSV UTF-8</p>
                    </div>
                    <button onClick={() => setSourceFile(null)} className="text-slate-300 hover:text-rose-500">
                      <X size={16} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Card 2: Configuration */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <span className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-tighter">
                <span className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center">2</span>
                Job Config
              </span>
              <button className="p-1 hover:bg-slate-100 rounded text-slate-400 transition-colors">
                <RotateCcw size={14} />
              </button>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-400 uppercase ml-1">Pilih Job Aktif</label>
                <select 
                  value={selectedJob}
                  onChange={(e) => setSelectedJob(e.target.value)}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-500 outline-none transition-all cursor-pointer"
                >
                  <option value="job-01">Transformasi Sales Bulanan</option>
                  <option value="job-02">Sinkronisasi Stok Gudang</option>
                  <option value="job-03">Format Laporan Keuangan</option>
                </select>
              </div>

              {/* Status Preflight dalam Card */}
              <div className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
                !preflightStatus ? 'bg-slate-50 border-slate-100 grayscale' :
                preflightStatus.status === 'success' ? 'bg-emerald-50 border-emerald-100' : 'bg-amber-50 border-amber-100'
              }`}>
                <div className={`mt-0.5 ${preflightStatus?.status === 'success' ? 'text-emerald-500' : 'text-slate-400'}`}>
                  <CheckCircle2 size={18} />
                </div>
                <div className="text-xs">
                  <p className="font-bold text-slate-700">Preflight Check</p>
                  <p className={preflightStatus ? 'text-slate-600' : 'text-slate-400'}>
                    {preflightStatus ? preflightStatus.message : 'Menunggu input file...'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Card 3: Execution Control */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <span className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-tighter">
                <span className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center">3</span>
                Execution
              </span>
              <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                appState === 'running' ? 'bg-indigo-100 text-indigo-600' : 
                appState === 'success' ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'
              }`}>
                {appState}
              </div>
            </div>

            <div className="flex-1 flex flex-col justify-center space-y-4">
              {appState !== 'success' ? (
                <button
                  disabled={appState !== 'ready'}
                  onClick={handleExecute}
                  className={`group w-full py-4 rounded-xl flex items-center justify-center gap-3 font-bold text-lg transition-all transform active:scale-95 ${
                    appState === 'ready' 
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200 cursor-pointer' 
                    : 'bg-slate-100 text-slate-300 cursor-not-allowed'
                  }`}
                >
                  {appState === 'running' ? (
                    <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  ) : (
                    <Play size={20} fill="currentColor" />
                  )}
                  <span>JALANKAN JOB</span>
                </button>
              ) : (
                <div className="space-y-3 animate-in zoom-in-95 duration-300">
                  <div className="bg-emerald-500 text-white p-4 rounded-xl flex items-center gap-3 shadow-lg shadow-emerald-100">
                    <CheckCircle2 size={24} />
                    <div>
                      <p className="font-bold">Berhasil!</p>
                      <p className="text-xs opacity-90">File output telah dibuat.</p>
                    </div>
                  </div>
                  <button 
                    onClick={handleReset}
                    className="w-full py-2 text-xs font-bold text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors border border-indigo-100"
                  >
                    MULAI SESI BARU
                  </button>
                </div>
              )}

              {(appState === 'running' || appState === 'success') && (
                <div className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400">
                    <span>PROGRESS</span>
                    <span>{Math.round(progress)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-600 transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Output Panel (Hanya muncul jika sukses) */}
        {appState === 'success' && (
          <div className="bg-white rounded-2xl border border-emerald-200 p-6 shadow-sm animate-in slide-in-from-top-4 duration-500">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-100 text-emerald-600 rounded-full">
                  <FolderOpen size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">File Output Tersedia</h3>
                  <p className="text-sm text-slate-500">Target: C:/Users/Admin/Desktop/Outputs/Result_Sales_01.xlsx</p>
                </div>
              </div>
              <div className="flex gap-3 w-full md:w-auto">
                <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-3 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:bg-slate-50 transition-all shadow-sm">
                  <FolderOpen size={18} className="text-indigo-500" />
                  Buka Folder Output
                </button>
                <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100">
                  <FileText size={18} />
                  Buka File Excel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Log Section */}
        <section className="bg-slate-900 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-[400px]">
          <div className="px-6 py-3 bg-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal size={16} className="text-indigo-400" />
              <h3 className="text-xs font-black uppercase tracking-widest text-slate-400">System Activity Logs</h3>
            </div>
            <div className="flex items-center gap-4 text-[10px] font-bold uppercase tracking-tight">
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Online
              </span>
              <span className="text-slate-500">Version 1.0.4-Stable</span>
            </div>
          </div>
          
          <div className="flex-1 p-6 overflow-y-auto font-mono text-[13px] leading-relaxed scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-4 mb-1 animate-in fade-in slide-in-from-left-1 duration-200">
                <span className="text-slate-600 shrink-0 select-none">[{log.time}]</span>
                <span className={
                  log.type === 'error' ? 'text-rose-400' : 
                  log.type === 'success' ? 'text-emerald-400' : 
                  log.type === 'info' ? 'text-indigo-300' : 'text-slate-300'
                }>
                  <span className="mr-2 opacity-30">$</span>
                  {log.msg}
                </span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </section>

      </main>

      {/* Settings Modal (tetap sama secara fungsional tapi dengan gaya V2) */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-md animate-in fade-in">
          <div className="w-full max-w-4xl bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200 border border-slate-200">
            <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <div className="bg-indigo-100 p-2 rounded-lg text-indigo-600">
                  <Settings size={20} />
                </div>
                <div>
                  <h2 className="font-extrabold text-lg text-slate-800">Job Configurations</h2>
                  <p className="text-xs text-slate-400 font-medium">Atur alur kerja dan file master untuk tiap job</p>
                </div>
              </div>
              <button onClick={() => setIsSettingsOpen(false)} className="p-2 hover:bg-slate-200 rounded-full transition-colors text-slate-400">
                <X size={24} />
              </button>
            </div>
            
            <div className="flex-1 flex overflow-hidden min-h-[500px]">
              {/* Sidebar Job List */}
              <div className="w-72 border-r border-slate-100 bg-slate-50/30 p-6 space-y-2 overflow-y-auto">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">DAFTAR JOB</p>
                {['Transformasi Sales', 'Stok Gudang', 'Laporan Keuangan', 'Data HR'].map((job, idx) => (
                  <button key={idx} className={`w-full text-left px-4 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-between group ${idx === 0 ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100' : 'hover:bg-slate-100 text-slate-600'}`}>
                    <span>{job}</span>
                    <ChevronRight size={14} className={idx === 0 ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} />
                  </button>
                ))}
                <button className="w-full flex items-center justify-center gap-2 py-3 border-2 border-dashed border-slate-200 rounded-xl text-xs font-bold text-slate-400 hover:border-indigo-300 hover:text-indigo-500 transition-all mt-4">
                  <Plus size={16} /> TAMBAH JOB BARU
                </button>
              </div>

              {/* Edit Form */}
              <div className="flex-1 p-10 overflow-y-auto">
                <div className="space-y-8 max-w-2xl">
                  <div className="grid grid-cols-2 gap-8">
                    <div className="space-y-2">
                      <label className="text-[11px] font-black text-slate-400 uppercase">Nama Pekerjaan</label>
                      <input type="text" defaultValue="Transformasi Sales Bulanan" className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[11px] font-black text-slate-400 uppercase">Status Aktif</label>
                      <div className="flex items-center gap-3 h-11">
                        <div className="w-12 h-6 bg-indigo-600 rounded-full relative p-1 cursor-pointer">
                          <div className="w-4 h-4 bg-white rounded-full absolute right-1"></div>
                        </div>
                        <span className="text-sm font-bold text-slate-700">Aktif</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-[11px] font-black text-slate-400 uppercase">File Konfigurasi (.yaml)</label>
                    <div className="flex gap-2">
                      <div className="flex-1 bg-slate-100 p-3 rounded-xl border border-slate-200 text-xs font-mono text-slate-500 truncate">
                        config/workflows/sales_transformation_v2.yaml
                      </div>
                      <button className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold hover:bg-slate-50 shadow-sm">Ganti</button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-[11px] font-black text-slate-400 uppercase">File Master / Template Excel</label>
                    <div className="border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                      <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-600">template_sales_report_2024.xlsx</span>
                        <div className="flex gap-2">
                          <button className="p-1.5 hover:bg-slate-200 rounded text-slate-400 transition-colors"><ExternalLink size={14}/></button>
                          <button className="p-1.5 hover:bg-rose-100 rounded text-rose-500 transition-colors"><Trash2 size={14}/></button>
                        </div>
                      </div>
                      <div className="p-6 text-center">
                        <div className="mx-auto w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mb-2 border border-slate-100">
                          <FileSpreadsheet className="text-slate-300" size={20} />
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed font-medium">Struktur template ini digunakan sebagai basis data hasil transformasi.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="px-8 py-5 border-t border-slate-100 flex items-center justify-end gap-3 bg-slate-50/50">
              <button onClick={() => setIsSettingsOpen(false)} className="px-6 py-2.5 rounded-xl text-sm font-bold text-slate-500 hover:bg-slate-100 transition-colors">Batal</button>
              <button onClick={() => setIsSettingsOpen(false)} className="px-8 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 shadow-lg shadow-indigo-100 transition-all">Simpan Perubahan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
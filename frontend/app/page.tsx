import ChatInterface from "../components/ChatInterface";
import { Mic, Code, FileText, LayoutDashboard } from "lucide-react";

export default function Home() {
  return (
    <div className="flex h-screen bg-[var(--bg-primary)] overflow-hidden font-sans">
      
      {/* Sidebar - Desktop Only */}
      <aside className="w-72 border-r border-[var(--border-primary)] bg-[#000000] hidden md:flex flex-col relative z-20">
        <div className="p-6 border-b border-[var(--border-primary)] bg-[#0A0A0B]">
          <div className="flex items-center gap-3 text-[var(--text-primary)] mb-2">
            <div className="p-2 bg-[#0A0A0B] border border-[var(--border-primary)] text-[var(--accent)]">
              <Mic size={20} />
            </div>
            <h1 className="font-bold text-2xl tracking-tight uppercase">Agent.</h1>
          </div>
          <p className="text-xs text-[var(--text-secondary)] font-mono tracking-widest uppercase mt-4">Local AI Engine</p>
        </div>

        <nav className="flex-1 px-4 py-8 space-y-4">
          <div className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest mb-4 px-2 font-mono pb-1 w-full text-left">Systems</div>
          
          <div className="flex items-center gap-3 px-3 py-3 bg-[#000000] text-[var(--accent)] border border-[var(--accent)] shadow-[0_0_15px_rgba(204,255,0,0.1)] transition-all cursor-pointer">
            <LayoutDashboard size={18} />
            <span className="text-sm font-bold uppercase tracking-wide">Active Session</span>
          </div>
        </nav>

        <div className="p-6 border-t border-[var(--border-primary)] bg-[var(--bg-secondary)]">
          <div className="p-5 border border-[var(--border-primary)] bg-[#000000]">
            <h4 className="text-[10px] font-bold text-[var(--text-secondary)] mb-4 uppercase tracking-widest font-mono border-b border-[var(--border-primary)] pb-2 text-left">Capabilities</h4>
            <div className="space-y-4 font-mono">
              <div className="flex items-center gap-3 text-xs text-[var(--text-primary)] font-semibold">
                <Code size={14} className="text-[var(--accent)]" />
                <span className="uppercase tracking-wider">Generator</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-[var(--text-primary)] font-semibold">
                <FileText size={14} className="text-[var(--accent)]" />
                <span className="uppercase tracking-wider">File I/O</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-[var(--text-primary)] font-semibold">
                <Mic size={14} className="text-[var(--danger)] animate-pulse" />
                <span className="uppercase tracking-wider">Audio Uplink</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative h-full bg-[#030303]">
        
        {/* Header - Mobile Only */}
        <header className="md:hidden flex items-center p-4 border-b border-[var(--border-primary)] bg-[var(--bg-secondary)] z-10">
          <div className="w-8 h-8 flex items-center justify-center mr-3 border border-[var(--border-primary)]">
            <Mic size={16} className="text-[var(--accent)]" />
          </div>
          <h1 className="font-bold text-xl text-[var(--text-primary)] uppercase font-mono">Agent.</h1>
        </header>

        {/* Chat Interface */}
        <div className="flex-1 relative z-10 w-full overflow-hidden">
          <ChatInterface />
        </div>
      </main>

    </div>
  );
}

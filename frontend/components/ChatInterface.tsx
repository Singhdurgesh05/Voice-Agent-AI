"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Bot, User, Download, FileText, Paperclip, X } from "lucide-react";
import AudioRecorder from "./AudioRecorder";
import ActionApproval, { PendingAction } from "./ActionApproval";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  transcription?: string;
  intent?: string;
  actions_taken?: string[];
  final_result?: string;
  pending_actions?: PendingAction[];
}

interface SummaryItem {
  action_id: string;
  message_id: string;
  summary: string;
  created_at: string;
  completed_at: string | null;
  original_length: number | null;
  summary_length: number | null;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [actionProcessingId, setActionProcessingId] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<SummaryItem[]>([]);
  const [isLoadingSummaries, setIsLoadingSummaries] = useState(false);
  const [isExportingSummaries, setIsExportingSummaries] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchHistory = async (sid: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/chat/sessions/${sid}/history`);
      if (!res.ok) return;
      const historyData = await res.json();
      const loadedMessages: Message[] = historyData.map((m: any, idx: number) => ({
        id: `hist-${idx}`,
        role: m.role,
        content: m.content
      }));
      setMessages(loadedMessages);
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
  };

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedId = localStorage.getItem("voice_agent_session_id");
    if (savedId) {
      setSessionId(savedId);
      fetchHistory(savedId);
    }
  }, []);

  // Persist session to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("voice_agent_session_id", sessionId);
    } else {
      localStorage.removeItem("voice_agent_session_id");
    }
  }, [sessionId]);

  const clearSession = () => {
    setSessionId(null);
    setMessages([]);
    setSummaries([]);
    localStorage.removeItem("voice_agent_session_id");
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleAudioSubmit(file);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle Text Submission
  const handleTextSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isProcessing) return;

    const userMsg = inputText.trim();
    setInputText("");
    await processInput(userMsg, null);
  };

  // Handle Audio Submission
  const handleAudioSubmit = async (audioBlob: Blob) => {
    await processInput(null, audioBlob);
  };

  // Process input via endpoints
  const processInput = async (text: string | null, audio: Blob | null) => {
    try {
      setIsProcessing(true);
      
      // Optimistic user message if text
      const tempId = Date.now().toString();
      if (text) {
        setMessages(prev => [...prev, { id: tempId, role: "user", content: text }]);
      } else if (audio) {
        setMessages(prev => [...prev, { id: tempId, role: "user", content: "🎤 (Audio Recording attached)" }]);
      }

      const formData = new FormData();
      if (sessionId) formData.append("session_id", sessionId);

      let url = "";
      if (audio) {
        formData.append("audio", audio, "recording.wav");
        url = "http://localhost:8000/api/chat/audio";
      } else if (text) {
        formData.append("message", text);
        url = "http://localhost:8000/api/chat/text";
      }

      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || "API error");

      if (data.session_id) setSessionId(data.session_id);

      // Create proper final sequence
      setMessages(prev => {
        // Remove optimistic
        const filtered = prev.filter(m => m.id !== tempId);
        
        // Add updated user message if we got transcription
        const finalUserText = data.transcription || text || "🎤 Audio";
        const userM = { id: `u-${data.message_id}`, role: "user" as const, content: finalUserText };

        const executedActions: string[] = (data.executed_actions || []).map((a: any) => {
          const actionName = a.tool_name || "unknown_tool";
          const actionMsg = a?.result?.message || "completed";
          return `${actionName}: ${actionMsg}`;
        });
        const pendingActions: string[] = (data.pending_actions || []).map((a: any) => {
          const actionName = a.tool_name || "unknown_tool";
          return `${actionName}: awaiting approval`;
        });
        const allActions = [...executedActions, ...pendingActions];
        
        // Add assistant reply
        const asstM = { 
          id: data.message_id, 
          role: "assistant" as const, 
          content: data.response,
          transcription: data.transcription || finalUserText,
          intent: data.intent || "unknown",
          actions_taken: allActions,
          final_result: data.response || "No response generated.",
          pending_actions: data.pending_actions || []
        };
        
        return [...filtered, userM, asstM];
      });

    } catch (error) {
      console.error("Chat Error:", error);
      setMessages(prev => [...prev, { 
        id: Date.now().toString(), 
        role: "assistant", 
        content: `❌ **Error:** Failed to process request.` 
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Action Approval
  const handleAction = async (actionId: string, endpoint: "approve" | "reject") => {
    try {
      setActionProcessingId(actionId);
      const res = await fetch(`http://localhost:8000/api/actions/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: actionId })
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail);

      // Remove from pending actions in UI and append a system message
      setMessages(prev => prev.map(msg => {
        if (!msg.pending_actions) return msg;
        return {
          ...msg,
          pending_actions: msg.pending_actions.filter(a => a.id !== actionId)
        };
      }));

      // Add feedback message
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "assistant",
        content: `✅ Action **${endpoint}d**: ${data.message || ""}`
      }]);

    } catch (error) {
      console.error("Action error:", error);
    } finally {
      setActionProcessingId(null);
    }
  };

  const fetchSummaries = async () => {
    if (!sessionId) return;
    try {
      setIsLoadingSummaries(true);
      const res = await fetch(`http://localhost:8000/api/actions/summaries/${sessionId}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch summaries");
      setSummaries(data.summaries || []);
    } catch (error) {
      console.error("Summary fetch error:", error);
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: "❌ **Error:** Failed to load summaries.",
        },
      ]);
    } finally {
      setIsLoadingSummaries(false);
    }
  };

  const exportSummaries = async () => {
    if (!sessionId) return;
    try {
      setIsExportingSummaries(true);
      const res = await fetch(`http://localhost:8000/api/actions/summaries/${sessionId}/export`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Export failed");
      }

      const blob = await res.blob();
      const fileUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = fileUrl;
      link.download = `${sessionId}.md`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(fileUrl);
    } catch (error) {
      console.error("Summary export error:", error);
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: "❌ **Error:** Failed to export summaries.",
        },
      ]);
    } finally {
      setIsExportingSummaries(false);
    }
  };

  return (
    <div className="flex flex-col h-full mx-auto max-w-5xl pt-8 pb-0">
      {sessionId && (
        <div className="px-6 mb-6">
          <div className="bg-[#000000] border border-[var(--border-primary)] p-4 flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)] font-mono font-bold uppercase tracking-wider">
                <span>Session ID: <span className="text-[var(--text-primary)] bg-[var(--bg-secondary)] px-2 py-1 border border-[var(--border-primary)] ml-1">{sessionId}</span></span>
                <button 
                  onClick={clearSession} 
                  title="Clear Session"
                  className="p-1 hover:text-[var(--danger)] hover:bg-[#111111] transition-colors border border-transparent hover:border-[var(--danger)]"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={fetchSummaries}
                  disabled={isLoadingSummaries}
                  className="px-4 py-2 bg-[#0A0A0B] border border-[var(--border-primary)] text-xs font-bold uppercase text-[var(--text-primary)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all disabled:opacity-50"
                >
                  {isLoadingSummaries ? "Loading..." : "Load Summaries"}
                </button>
                <button
                  onClick={exportSummaries}
                  disabled={isExportingSummaries}
                  className="px-4 py-2 bg-[var(--accent)] border border-[var(--accent)] text-[#000000] text-xs font-bold uppercase hover:bg-[var(--accent-hover)] transition-all disabled:opacity-50 inline-flex items-center gap-2 shadow-[0_0_15px_rgba(204,255,0,0.15)]"
                >
                  <Download size={14} />
                  {isExportingSummaries ? "Exporting..." : "Download .md"}
                </button>
              </div>
            </div>

            {summaries.length > 0 && (
              <div className="max-h-44 overflow-y-auto space-y-4 pr-2 mt-4 pt-4 border-t border-[var(--border-primary)]">
                {summaries.map((item, idx) => (
                  <div key={item.action_id} className="border border-[var(--border-primary)] bg-[#0A0A0B] p-4 hover:border-[var(--accent)] transition-colors">
                    <div className="flex items-center gap-2 text-xs text-[var(--accent)] font-bold font-mono pb-2 mb-2 uppercase tracking-wider">
                      <FileText size={14} />
                      <span>Summary Block 0{idx + 1}</span>
                    </div>
                    <p className="text-sm text-[var(--text-primary)] font-mono leading-relaxed">{item.summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 mb-8 space-y-8">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center opacity-60">
            <Bot size={80} className="mb-6 text-[var(--border-primary)]" strokeWidth={1} />
            <h2 className="text-3xl font-bold uppercase tracking-widest mb-2 font-mono text-[var(--text-primary)]">System Idle</h2>
            <p className="text-sm font-mono text-[var(--text-secondary)]">Awaiting telemetry. Speak or type to engage.</p>
          </div>
        )}
        
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`flex gap-6 animate-fade-in ${message.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div className={`w-12 h-12 flex items-center justify-center shrink-0 border border-[var(--border-primary)] ${
              message.role === "user" 
                ? "bg-[var(--bg-secondary)] text-[var(--accent)]" 
                : "bg-[#0A0A0B] text-[var(--text-primary)]"
            }`}>
              {message.role === "user" ? <User size={20} strokeWidth={2} /> : <Bot size={24} strokeWidth={1.5} />}
            </div>
            
            <div className={`flex flex-col max-w-[85%] ${message.role === "user" ? "items-end" : ""}`}>
              <div className={`p-6 border border-[var(--border-primary)] ${
                message.role === "user"
                  ? "bg-[#0A0A0B] text-[var(--text-primary)] border-r-2 border-[var(--accent)]"
                  : "bg-[#000000] text-[var(--text-primary)] border-l-2 border-l-[var(--danger)]"
              }`}>
                {message.role === "assistant" && (
                  <div className="mb-4 text-[11px] font-mono space-y-2 text-[var(--text-secondary)] border-b border-[var(--border-primary)] pb-4 uppercase tracking-wider">
                    {message.transcription && (
                      <div className="flex gap-2">
                        <span className="text-[var(--text-muted)] w-24 shrink-0">Input:</span> 
                        <span className="text-[var(--text-primary)]">{message.transcription}</span>
                      </div>
                    )}
                    {message.intent && (
                      <div className="flex gap-2">
                        <span className="text-[var(--text-muted)] w-24 shrink-0">Parsed Intent:</span> 
                        <span className="text-[var(--accent)]">{message.intent}</span>
                      </div>
                    )}
                    {message.actions_taken && message.actions_taken.length > 0 && (
                      <div className="flex gap-2">
                        <span className="text-[var(--text-muted)] w-24 shrink-0">Seq. Actions:</span> 
                        <span className="text-[var(--danger)]">{message.actions_taken.join(" | ")}</span>
                      </div>
                    )}
                  </div>
                )}
                {message.content && (
                  <div className={`prose prose-sm max-w-none prose-invert ${message.role === "user" ? "font-mono text-sm leading-relaxed text-[var(--accent)]" : ""}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
              
              {/* Render any pending actions below the assistant's message */}
              {message.pending_actions?.map(action => (
                <div key={action.id} className="w-full mt-4">
                  <ActionApproval 
                    action={action} 
                    onApprove={(id) => handleAction(id, "approve")}
                    onReject={(id) => handleAction(id, "reject")}
                    isProcessingId={actionProcessingId}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
        
        {isProcessing && (
          <div className="flex gap-6 animate-fade-in">
            <div className="w-12 h-12 bg-[#0A0A0B] border border-[var(--border-primary)] flex items-center justify-center shrink-0">
              <Bot size={24} strokeWidth={1.5} className="animate-pulse text-[var(--accent)]" />
            </div>
            <div className="p-5 border border-[var(--border-primary)] bg-[#000000] flex items-center gap-3 border-l-2 border-l-[var(--accent)] shadow-[0_0_15px_rgba(204,255,0,0.05)]">
              <div className="w-2 h-2 bg-[var(--accent)] animate-pulse-ring" style={{ animationDelay: "0ms" }} />
              <div className="w-2 h-2 bg-[var(--accent)] animate-pulse-ring" style={{ animationDelay: "200ms" }} />
              <div className="w-2 h-2 bg-[var(--danger)] animate-pulse-ring" style={{ animationDelay: "400ms" }} />
              <span className="ml-3 text-xs font-mono font-bold uppercase tracking-wider text-[var(--accent)]">Processing Telemetry...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="w-full bg-[#000000] border-t border-[var(--border-primary)] p-4 z-20">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <AudioRecorder onRecordingComplete={handleAudioSubmit} isProcessing={isProcessing} />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            title="Upload audio file"
            className="p-4 bg-[#0A0A0B] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--accent)] hover:border-[var(--accent)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Paperclip size={20} />
          </button>
          <input 
            type="file" 
            ref={fileInputRef} 
            accept="audio/*" 
            className="hidden" 
            onChange={handleFileUpload} 
          />

          <form onSubmit={handleTextSubmit} className="flex-1 flex items-center bg-[#0A0A0B] border border-[var(--border-primary)] focus-within:border-[var(--accent)] focus-within:shadow-[0_0_15px_rgba(204,255,0,0.1)] transition-all">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isProcessing}
              placeholder="Or type your command here..."
              className="flex-1 bg-transparent border-none text-[var(--text-primary)] font-mono text-sm focus:outline-none placeholder:text-[var(--border-primary)] p-4"
            />
            <button 
              type="submit" 
              disabled={isProcessing || !inputText.trim()}
              className="p-4 bg-[var(--accent)] text-[#000000] hover:bg-[var(--accent-hover)] transition-colors border-l border-[var(--border-primary)] disabled:opacity-50 disabled:cursor-not-allowed uppercase font-bold tracking-widest text-xs flex items-center gap-2 shadow-[0_0_15px_rgba(204,255,0,0.2)]"
            >
              <span>Transmit</span>
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

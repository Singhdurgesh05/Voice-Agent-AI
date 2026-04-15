"use client";

import { Check, X, Code2, FileText, Loader2 } from "lucide-react";

export interface PendingAction {
  id: string;
  tool_name: string;
  tool_args: Record<string, any>;
  status: string;
}

interface ActionApprovalProps {
  action: PendingAction;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  isProcessingId: string | null;
}

export default function ActionApproval({ action, onApprove, onReject, isProcessingId }: ActionApprovalProps) {
  const isCode = action.tool_name === "write_code";
  const isFolder = action.tool_name === "create_folder";
  const targetPath = action.tool_args.filename || action.tool_args.foldername || "unknown_target";
  const contentPreview = action.tool_args.code 
    ? action.tool_args.code.substring(0, 150) + (action.tool_args.code.length > 150 ? "..." : "")
    : null;

  const processing = isProcessingId === action.id;

  return (
    <div className="p-4 my-4 border border-[var(--danger)] bg-[#000000] relative shadow-[0_0_15px_rgba(255,69,0,0.1)] animate-slide-up">
      <div className="absolute top-0 right-0 px-2 py-1 bg-[var(--danger)] text-white text-[9px] font-bold tracking-widest uppercase">
        Awaiting Auth
      </div>
      <div className="flex items-start gap-4 mt-2">
        <div className="p-2 border border-[var(--danger)] bg-[#0A0A0B] text-[var(--danger)]">
          {isCode ? <Code2 size={20} /> : <FileText size={20} />}
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-bold text-[var(--text-primary)] mb-1 uppercase tracking-wide">
            Action Requirement: {isCode ? "Execute Code Segment" : isFolder ? "Create Directory" : "Create File"}
          </h4>
          <p className="text-xs text-[var(--text-secondary)] mb-4 font-mono">
            Target Destination: <strong className="text-[var(--accent)] font-normal">{targetPath}</strong>
          </p>
          
          {contentPreview && (
            <div className="code-block mb-4 border-l-2 border-l-[var(--danger)]">
              <pre><code>{contentPreview}</code></pre>
            </div>
          )}

          <div className="flex gap-3">
            <button 
              onClick={() => onApprove(action.id)}
              disabled={processing}
              className="px-4 py-2 text-[10px] font-bold uppercase tracking-widest bg-[var(--accent)] text-black hover:bg-[var(--accent-hover)] transition-colors flex items-center justify-center gap-2 shadow-[0_0_10px_var(--accent-glow)] w-32"
            >
              {processing ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} strokeWidth={3} />} Authorize
            </button>
            <button 
              onClick={() => onReject(action.id)}
              disabled={processing}
              className="px-4 py-2 text-[10px] font-bold uppercase tracking-widest bg-transparent text-[var(--text-primary)] border border-[var(--border-primary)] hover:border-[var(--danger)] hover:text-[var(--danger)] transition-colors flex items-center justify-center gap-2 w-32"
            >
              <X size={14} strokeWidth={2} /> Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

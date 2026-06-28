import React from 'react'
import { X, Brain, CheckCircle, HelpCircle, AlertTriangle, Key, Activity } from 'lucide-react'
import type { IntentSummary } from '../../types'

interface ExplainabilityModalProps {
  intent: IntentSummary
  onClose: () => void
}

export const ExplainabilityModal: React.FC<ExplainabilityModalProps> = ({ intent, onClose }) => {
  const getConfidenceLevel = (score: number) => {
    if (score >= 0.85) return { text: 'High Certainty', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15' }
    if (score >= 0.6) return { text: 'Medium Certainty', color: 'text-amber-400 bg-amber-500/10 border-amber-500/15' }
    return { text: 'Uncertain / Low Confidence', color: 'text-rose-400 bg-rose-500/10 border-rose-500/15' }
  }

  const confidence = getConfidenceLevel(intent.confidence)

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="w-full max-w-lg glass bg-[#1e293b] border border-slate-700/80 shadow-2xl rounded-xl overflow-hidden animate-in fade-in zoom-in duration-150">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-700/60 flex items-center justify-between bg-[#0f172a]/30">
          <div className="flex items-center gap-2 text-indigo-400">
            <Brain className="h-5 w-5" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">AI Intent Explainability</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 cursor-pointer">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Classification details */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Detected Objective</span>
              <span className="text-base font-bold text-slate-200 mt-0.5 block">{intent.detected_intent}</span>
            </div>
            <div className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${confidence.color}`}>
              {confidence.text} ({Math.round(intent.confidence * 100)}%)
            </div>
          </div>

          {/* Reasoning */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">AI Reasoning / Rationale</span>
            <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700 text-xs text-slate-300 leading-relaxed italic">
              {intent.reasoning || 'No narrative reasoning returned for this transaction.'}
            </div>
          </div>

          {/* Memory Influenced */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Influenced Memory Facts</span>
            <div className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700 text-xs text-slate-300 leading-relaxed">
              {intent.memory_influenced ? (
                <p className="text-slate-300">{intent.memory_influenced}</p>
              ) : (
                <p className="text-slate-500 italic">No existing customer facts shaped this prompt. Classified entirely from current utterance.</p>
              )}
            </div>
          </div>

          {/* Keywords */}
          {intent.detected_keywords && intent.detected_keywords.length > 0 && (
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block flex items-center gap-1">
                <Key className="h-3 w-3 text-indigo-400" />
                Detected Keyword Matches
              </span>
              <div className="flex flex-wrap gap-1.5">
                {intent.detected_keywords.map((kw, i) => (
                  <span key={i} className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/15">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Entities Table */}
          <div className="space-y-2 pt-2 border-t border-slate-700/30">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Extracted Context Details</span>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded bg-slate-800/20 border border-slate-700/50">
                <span className="text-slate-500 block">Urgency</span>
                <span className="font-semibold text-slate-300 capitalize">{intent.urgency}</span>
              </div>
              <div className="p-2.5 rounded bg-slate-800/20 border border-slate-700/50">
                <span className="text-slate-500 block">Stage</span>
                <span className="font-semibold text-slate-300 capitalize">{intent.buying_stage || 'Unknown'}</span>
              </div>
              <div className="p-2.5 rounded bg-slate-800/20 border border-slate-700/50">
                <span className="text-slate-500 block">Budget Target</span>
                <span className="font-semibold text-slate-300">{intent.budget || 'None'}</span>
              </div>
              <div className="p-2.5 rounded bg-slate-800/20 border border-slate-700/50">
                <span className="text-slate-500 block">Preferred Location</span>
                <span className="font-semibold text-slate-300">{intent.location || 'None'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#0f172a]/20 border-t border-slate-700/60 flex justify-end">
          <button onClick={onClose} className="btn-ghost text-xs px-4 py-2 cursor-pointer">
            Close Panel
          </button>
        </div>

      </div>
    </div>
  )
}

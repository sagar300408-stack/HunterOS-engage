import React from 'react'
import type { ConversationSummary } from '../../types'
import { Phone, ArrowRightLeft, Clock } from 'lucide-react'

interface ConversationCardProps {
  summary: ConversationSummary
  active: boolean
  onClick: () => void
}

export const ConversationCard: React.FC<ConversationCardProps> = ({ summary, active, onClick }) => {
  const getStageColor = (stage: string | undefined) => {
    switch (stage) {
      case 'Purchase Ready':
        return 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
      case 'Negotiation':
        return 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
      case 'Ready to Schedule':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
      case 'Comparing Options':
        return 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
      case 'Research':
      default:
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
    }
  }

  const getUrgencyColor = (urgency: string | undefined) => {
    switch (urgency?.toLowerCase()) {
      case 'high':
        return 'bg-rose-500'
      case 'medium':
        return 'bg-amber-500'
      case 'low':
        return 'bg-slate-500'
      default:
        return 'bg-slate-600'
    }
  }

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all duration-200 cursor-pointer relative overflow-hidden ${
        active
          ? 'bg-indigo-500/10 border-indigo-500/40 shadow-md shadow-indigo-500/5'
          : 'bg-[#1e293b]/40 border-slate-700/50 hover:bg-[#1e293b]/80 hover:border-slate-600'
      }`}
    >
      {active && (
        <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
      )}

      <div className="flex justify-between items-start gap-2">
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-200 truncate">
            {summary.customer_name || summary.customer_phone}
          </p>
          <div className="flex items-center gap-1 text-[11px] text-slate-400 mt-0.5">
            <Phone className="h-3 w-3 shrink-0" />
            <span>{summary.customer_phone}</span>
          </div>
        </div>

        <span className="text-[10px] text-slate-500 font-mono shrink-0">
          {summary.last_activity ? new Date(summary.last_activity).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
        </span>
      </div>

      <p className="text-xs text-slate-300 mt-2.5 truncate leading-relaxed">
        {summary.last_message_direction === 'outgoing' && (
          <span className="text-indigo-400 font-semibold mr-1">AI:</span>
        )}
        {summary.last_message || <span className="text-slate-500 italic">No messages</span>}
      </p>

      <div className="flex items-center justify-between mt-3.5 pt-3 border-t border-slate-700/30">
        <div className="flex items-center gap-1.5 min-w-0">
          {summary.buying_stage && (
            <span className={`badge ${getStageColor(summary.buying_stage)} truncate`}>
              {summary.buying_stage}
            </span>
          )}
          {summary.detected_intent && (
            <span className="text-[10px] font-medium text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700 truncate">
              {summary.detected_intent}
            </span>
          )}
        </div>

        {summary.urgency && summary.urgency !== 'unknown' && (
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`h-1.5 w-1.5 rounded-full ${getUrgencyColor(summary.urgency)}`}></span>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              {summary.urgency}
            </span>
          </div>
        )}
      </div>
    </button>
  )
}

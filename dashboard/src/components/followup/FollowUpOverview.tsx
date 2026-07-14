import React from 'react'
import type { FollowUpOverviewStats } from '../../types'
import { CalendarClock, AlertCircle, Send, CheckCircle2 } from 'lucide-react'

export default function FollowUpOverview({ stats, loading }: { stats?: FollowUpOverviewStats, loading: boolean }) {
  if (loading) {
    return <div className="h-24 card skeleton"></div>
  }
  
  if (!stats) return null
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="card p-4 flex items-center justify-between group">
        <div>
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Pending Queue</span>
          <span className="text-2xl font-bold text-slate-200 mt-1 block font-mono">{stats.pending_followups}</span>
        </div>
        <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          <CalendarClock className="h-5 w-5" />
        </div>
      </div>
      
      <div className="card p-4 flex items-center justify-between group">
        <div>
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Due Today</span>
          <span className="text-2xl font-bold text-slate-200 mt-1 block font-mono">{stats.due_today}</span>
        </div>
        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Send className="h-5 w-5" />
        </div>
      </div>
      
      <div className="card p-4 flex items-center justify-between group">
        <div>
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Sent Today</span>
          <span className="text-2xl font-bold text-slate-200 mt-1 block font-mono">{stats.sent_today}</span>
        </div>
        <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
          <CheckCircle2 className="h-5 w-5" />
        </div>
      </div>
      
      <div className="card p-4 flex items-center justify-between group">
        <div>
          <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">Needs Review</span>
          <span className="text-2xl font-bold text-slate-200 mt-1 block font-mono">{stats.paused_needs_review}</span>
        </div>
        <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertCircle className="h-5 w-5" />
        </div>
      </div>
    </div>
  )
}

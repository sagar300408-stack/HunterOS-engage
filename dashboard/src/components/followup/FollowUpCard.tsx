import React from 'react'
import type { FollowUpQueueSummary } from '../../types'
import { Clock, Play, Pause, AlertTriangle } from 'lucide-react'

interface FollowUpCardProps {
  item: FollowUpQueueSummary
  onClick: () => void
}

export default function FollowUpCard({ item, onClick }: FollowUpCardProps) {
  const isOverdue = new Date(item.scheduled_for) < new Date() && item.status === 'scheduled'
  
  return (
    <div 
      className={`card p-4 hover:border-indigo-500/50 cursor-pointer transition-all ${isOverdue ? 'border-rose-500/30 bg-rose-500/5' : ''}`}
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-200">{item.customer_name || 'Unknown Lead'}</span>
          <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border ${
            item.status === 'scheduled' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' :
            item.status === 'executing' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
            item.status === 'sent' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
            item.status === 'replied' ? 'bg-teal-500/10 text-teal-400 border-teal-500/20' :
            item.status === 'paused' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
            'bg-rose-500/10 text-rose-400 border-rose-500/20'
          }`}>
            {item.status}
          </span>
        </div>
        {item.human_paused && (
          <div className="text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 border border-rose-500/20">
            <Pause className="h-3 w-3" /> PAUSED
          </div>
        )}
      </div>
      
      <div className="text-xs text-slate-400 mb-3 line-clamp-1">
        <span className="text-slate-300 font-semibold">{item.strategy?.replace('_', ' ')}:</span> {item.reason}
      </div>
      
      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
        <div className="flex items-center gap-1.5">
          <Clock className={`h-3.5 w-3.5 ${isOverdue ? 'text-rose-400' : ''}`} />
          <span className={isOverdue ? 'text-rose-400 font-bold' : ''}>
            {new Date(item.scheduled_for).toLocaleString()}
          </span>
        </div>
        {item.retry_count > 0 && (
          <div className="flex items-center gap-1 text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5" />
            Retry {item.retry_count}
          </div>
        )}
      </div>
    </div>
  )
}

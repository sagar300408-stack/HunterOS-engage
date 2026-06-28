import React from 'react'
import { Activity, RefreshCw, CircleDot } from 'lucide-react'
import type { ActivityEvent } from '../../types'

interface ActivityTimelineProps {
  events: ActivityEvent[] | undefined
  loading: boolean
  onRefresh: () => void
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ events, loading, onRefresh }) => {
  const getEventMarkerColor = (type: string) => {
    switch (type) {
      case 'customer_created':
        return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
      case 'memory_summarized':
        return 'text-indigo-400 border-indigo-500/30 bg-indigo-500/10'
      case 'budget_detected':
      case 'timeline_detected':
      case 'location_detected':
      case 'interest_detected':
        return 'text-amber-400 border-amber-500/30 bg-amber-500/10'
      default:
        return 'text-slate-400 border-slate-700 bg-slate-800/40'
    }
  }

  return (
    <div className="card space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-base font-bold text-slate-200">AI Pipeline Activity Feed</h2>
          <p className="text-xs text-slate-400 mt-1">Real-time background pipeline event registration</p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="btn-ghost p-2 text-slate-400 hover:text-slate-200 cursor-pointer"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="h-64 skeleton"></div>
      ) : !events || events.length === 0 ? (
        <div className="text-center py-12 text-slate-500 text-xs italic">
          No pipeline events recorded.
        </div>
      ) : (
        <div className="relative pl-6 space-y-6 before:absolute before:inset-y-1 before:left-[9px] before:w-0.5 before:bg-slate-700">
          {events.map((ev) => {
            const color = getEventMarkerColor(ev.event_type)
            return (
              <div key={ev.id} className="relative flex gap-4 items-start text-xs slide-in-right">
                
                {/* Node marker indicator */}
                <span className={`absolute -left-[22px] top-1.5 h-3.5 w-3.5 rounded-full border flex items-center justify-center bg-[#1e293b] z-10`}>
                  <CircleDot className={`h-1.5 w-1.5 ${color.split(' ')[0]}`} />
                </span>

                <div className="flex-1 p-3.5 rounded-xl border border-slate-800 bg-slate-800/20 hover:border-slate-700 transition-all">
                  <div className="flex justify-between items-start">
                    <span className="font-bold text-slate-300">{ev.description}</span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(ev.created_at).toLocaleTimeString()}
                    </span>
                  </div>

                  {(ev.customer_name || ev.customer_phone) && (
                    <span className="text-[10px] text-indigo-400 font-medium block mt-1">
                      Customer: {ev.customer_name || ev.customer_phone} ({ev.customer_phone})
                    </span>
                  )}

                  {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                    <div className="mt-2 bg-[#0f172a]/30 rounded p-2 border border-slate-800 font-mono text-[9px] text-slate-400 overflow-x-auto">
                      <pre>{JSON.stringify(ev.metadata, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

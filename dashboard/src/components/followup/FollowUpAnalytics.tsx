import React from 'react'
import type { FollowUpOverviewStats } from '../../types'

export default function FollowUpAnalytics({ stats, loading }: { stats?: FollowUpOverviewStats, loading: boolean }) {
  if (loading) return <div className="card h-64 skeleton"></div>
  if (!stats || !stats.strategy_distribution) return null
  
  const entries = Object.entries(stats.strategy_distribution).sort((a, b) => b[1] - a[1])
  const max = Math.max(...entries.map(e => e[1]), 1)
  
  return (
    <div className="card p-5 h-full flex flex-col">
      <h3 className="font-bold text-slate-200 text-sm mb-4">Strategy Distribution</h3>
      
      <div className="flex-1 space-y-4 overflow-y-auto pr-2">
        {entries.length === 0 ? (
          <div className="text-slate-500 text-xs italic">No strategy data yet.</div>
        ) : (
          entries.map(([strategy, count]) => (
            <div key={strategy}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium capitalize">{strategy.replace('_', ' ')}</span>
                <span className="text-slate-400 font-mono">{count}</span>
              </div>
              <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-indigo-500 rounded-full transition-all duration-1000" 
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

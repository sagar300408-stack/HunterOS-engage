import React from 'react'
import { AlertTriangle, TrendingUp, TrendingDown, Minus, ShieldCheck, Zap } from 'lucide-react'

interface LeadHealthBadgeProps {
  score: number
  band: 'Excellent' | 'Good' | 'Moderate' | 'At Risk' | 'Critical'
  reasons: string[]
  positive_signals: string[]
  recommendation?: string
  mode?: 'badge' | 'full'
}

export default function LeadHealthBadge({ score, band, reasons, positive_signals, recommendation, mode = 'badge' }: LeadHealthBadgeProps) {
  let color = 'text-slate-400 bg-slate-500/10 border-slate-500/20'
  let Icon = Minus
  
  if (band === 'Excellent') {
    color = 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    Icon = TrendingUp
  } else if (band === 'Good') {
    color = 'text-teal-400 bg-teal-500/10 border-teal-500/20'
    Icon = ShieldCheck
  } else if (band === 'Moderate') {
    color = 'text-amber-400 bg-amber-500/10 border-amber-500/20'
    Icon = Minus
  } else if (band === 'At Risk') {
    color = 'text-orange-400 bg-orange-500/10 border-orange-500/20'
    Icon = TrendingDown
  } else if (band === 'Critical') {
    color = 'text-rose-400 bg-rose-500/10 border-rose-500/20'
    Icon = AlertTriangle
  }

  if (mode === 'badge') {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-bold tracking-wide uppercase ${color}`}>
        <Icon className="h-3 w-3" />
        {score} - {band}
      </div>
    )
  }

  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-slate-900/40 rounded-lg">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold opacity-80 uppercase tracking-widest block">Lead Health</span>
            <span className="text-xl font-bold font-mono">{score} <span className="opacity-70 text-sm">/ 100</span></span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] font-bold opacity-80 uppercase tracking-widest block">Band</span>
          <span className="text-lg font-bold">{band}</span>
        </div>
      </div>
      
      <div className="space-y-2 mt-4 text-xs bg-slate-900/30 p-3 rounded-lg">
        {recommendation && (
          <div className="mb-2 pb-2 border-b border-white/10 flex items-start gap-2">
            <Zap className="h-4 w-4 shrink-0 mt-0.5" />
            <p className="font-semibold">{recommendation}</p>
          </div>
        )}
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="opacity-70 font-semibold mb-1 block">Signals</span>
            <ul className="space-y-1">
              {positive_signals.length > 0 ? positive_signals.map((r, i) => (
                <li key={i} className="flex items-center gap-1"><span className="text-emerald-400">+</span> {r}</li>
              )) : <li className="opacity-50 italic">None</li>}
            </ul>
          </div>
          <div>
            <span className="opacity-70 font-semibold mb-1 block">Risk Factors</span>
            <ul className="space-y-1">
              {reasons.length > 0 ? reasons.map((r, i) => (
                <li key={i} className="flex items-center gap-1"><span className="text-rose-400">-</span> {r}</li>
              )) : <li className="opacity-50 italic">None</li>}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

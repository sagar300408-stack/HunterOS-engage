import React from 'react'
import { Server, ShieldCheck, Database, HardDrive, RefreshCw } from 'lucide-react'
import type { SystemHealth as SystemHealthType } from '../../types'

interface SystemHealthProps {
  health: SystemHealthType | undefined
  loading: boolean
  onRefresh: () => void
}

export const SystemHealth: React.FC<SystemHealthProps> = ({ health, loading, onRefresh }) => {
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'online':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
          dot: 'bg-emerald-500 pulse-green',
          text: 'Operational',
        }
      case 'warning':
        return {
          bg: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
          dot: 'bg-amber-500 pulse-amber',
          text: 'Degraded Performance',
        }
      case 'offline':
        return {
          bg: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
          dot: 'bg-rose-500',
          text: 'Outage',
        }
      case 'not_configured':
      default:
        return {
          bg: 'bg-slate-500/10 border-slate-500/20 text-slate-400',
          dot: 'bg-slate-500',
          text: 'Not Configured',
        }
    }
  }

  const getServiceIcon = (name: string) => {
    const n = name.toLowerCase()
    if (n.includes('postgre') || n.includes('db')) return Database
    if (n.includes('openai') || n.includes('worker') || n.includes('ai')) return Server
    return HardDrive
  }

  return (
    <div className="card space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-base font-bold text-slate-200">System Infrastructure Health</h2>
          <p className="text-xs text-slate-400 mt-1">Real-time dependency operational verification</p>
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card-elevated p-4 h-24 skeleton"></div>
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Overall Health Status Bar */}
          <div
            className={`flex items-center gap-3 p-4 rounded-xl border ${
              health?.overall === 'healthy'
                ? 'bg-emerald-500/5 border-emerald-500/10 text-emerald-400'
                : health?.overall === 'degraded'
                ? 'bg-amber-500/5 border-amber-500/10 text-amber-400'
                : 'bg-rose-500/5 border-rose-500/10 text-rose-400'
            }`}
          >
            <ShieldCheck className="h-6 w-6 shrink-0" />
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider">
                Overall Status:{' '}
                {health?.overall === 'healthy'
                  ? 'All Systems Operational'
                  : health?.overall === 'degraded'
                  ? 'Systems Degraded'
                  : 'Critical Outage'}
              </p>
              <span className="text-xs text-slate-400 block mt-0.5">
                Last checked: {health?.checked_at ? new Date(health.checked_at).toLocaleTimeString() : '—'}
              </span>
            </div>
          </div>

          {/* Grid of Health Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {health?.services.map((svc) => {
              const Icon = getServiceIcon(svc.name)
              const styles = getStatusStyle(svc.status)

              return (
                <div
                  key={svc.name}
                  className="p-4 rounded-xl border border-slate-700 bg-slate-800/40 hover:border-slate-600 transition-all flex flex-col justify-between h-28"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-slate-700/50 text-slate-300">
                        <Icon className="h-4.5 w-4.5" />
                      </div>
                      <span className="text-sm font-semibold text-slate-200">{svc.name}</span>
                    </div>
                    <span className={`status-dot ${styles.dot}`}></span>
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs text-slate-400">{styles.text}</span>
                    {svc.latency_ms !== undefined && svc.latency_ms !== null && (
                      <span className="text-xs font-mono font-bold text-indigo-400">
                        {svc.latency_ms} ms
                      </span>
                    )}
                  </div>
                  {svc.detail && (
                    <p className="text-[10px] text-rose-400 mt-1 truncate">{svc.detail}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

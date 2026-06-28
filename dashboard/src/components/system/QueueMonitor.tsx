import React from 'react'
import { Cpu, AlertTriangle, CheckCircle2, Play, RefreshCw, Clock } from 'lucide-react'
import type { QueueStatus } from '../../types'

interface QueueMonitorProps {
  queue: QueueStatus | undefined
  loading: boolean
  onRefresh: () => void
}

export const QueueMonitor: React.FC<QueueMonitorProps> = ({ queue, loading, onRefresh }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/10'
      case 'running':
        return 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/10'
      case 'failed':
        return 'bg-rose-500/10 text-rose-400 border border-rose-500/10'
      case 'pending':
      default:
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/10'
    }
  }

  return (
    <div className="card space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-base font-bold text-slate-200">Asynchronous Queue Monitor</h2>
          <p className="text-xs text-slate-400 mt-1">Background processes and scheduled task workers</p>
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
      ) : (
        <div className="space-y-6">
          {/* Quick Counter Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-700 bg-slate-800/20 text-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Pending</span>
              <p className="text-2xl font-bold text-slate-200 mt-1 font-mono">{queue?.pending ?? 0}</p>
            </div>
            <div className="p-4 rounded-xl border border-slate-700 bg-slate-800/20 text-center">
              <span className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider">Running</span>
              <p className="text-2xl font-bold text-indigo-400 mt-1 font-mono">{queue?.running ?? 0}</p>
            </div>
            <div className="p-4 rounded-xl border border-slate-700 bg-slate-800/20 text-center">
              <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">Completed Today</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1 font-mono">{queue?.completed_today ?? 0}</p>
            </div>
            <div className="p-4 rounded-xl border border-slate-700 bg-slate-800/20 text-center">
              <span className="text-[10px] uppercase font-bold text-rose-400 tracking-wider">Failed</span>
              <p className="text-2xl font-bold text-rose-400 mt-1 font-mono">{queue?.failed ?? 0}</p>
            </div>
          </div>

          {/* Job execution log */}
          <div className="border border-[#334155] rounded-xl overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#0f172a]/60 text-slate-400 border-b border-[#334155] uppercase font-bold tracking-wider">
                  <th className="p-3">Job Type</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Run Count</th>
                  <th className="p-3">Scheduled At</th>
                  <th className="p-3">Completed At</th>
                  <th className="p-3 text-right">Job ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#334155] bg-[#1e293b]/40">
                {(!queue?.jobs || queue.jobs.length === 0) ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No background jobs currently registered in the database.
                    </td>
                  </tr>
                ) : (
                  queue.jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-800/40">
                      <td className="p-3 font-semibold text-slate-200">{job.job_type}</td>
                      <td className="p-3">
                        <span className={`badge ${getStatusBadge(job.status)}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="p-3 font-mono">{job.run_count}</td>
                      <td className="p-3 text-slate-400">
                        {new Date(job.scheduled_at).toLocaleString()}
                      </td>
                      <td className="p-3 text-slate-400">
                        {job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}
                      </td>
                      <td className="p-3 text-right text-slate-500 font-mono text-[10px]">{job.id.substring(0, 8)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

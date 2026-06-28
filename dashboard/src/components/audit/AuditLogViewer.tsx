import React from 'react'
import { History, Shield, Info, RefreshCw } from 'lucide-react'
import type { AuditLog } from '../../types'

interface AuditLogViewerProps {
  logs: AuditLog[] | undefined
  loading: boolean
  onRefresh: () => void
}

export const AuditLogViewer: React.FC<AuditLogViewerProps> = ({ logs, loading, onRefresh }) => {
  return (
    <div className="card space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-indigo-400" />
          <div>
            <h2 className="text-base font-bold text-slate-200">Compliance Audit Trail</h2>
            <p className="text-xs text-slate-400 mt-1">Immutable trace log of all manual operator overrides</p>
          </div>
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
      ) : !logs || logs.length === 0 ? (
        <div className="text-center py-12 text-slate-500 text-xs italic">
          No audit log entries recorded.
        </div>
      ) : (
        <div className="border border-[#334155] rounded-xl overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#0f172a]/60 text-slate-400 border-b border-[#334155] uppercase font-bold tracking-wider">
                <th className="p-3">Action</th>
                <th className="p-3">Operator</th>
                <th className="p-3">Target</th>
                <th className="p-3">Changes Summary</th>
                <th className="p-3">Timestamp</th>
                <th className="p-3 text-right">IP Address</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#334155] bg-[#1e293b]/40">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40">
                  <td className="p-3">
                    <span className="inline-flex items-center gap-1.5 font-semibold text-slate-200">
                      <Shield className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                      {log.action.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                  <td className="p-3 text-slate-300 font-medium">{log.user_email || 'System'}</td>
                  <td className="p-3 text-slate-400">
                    <span className="font-semibold text-slate-300">{log.target_type}</span>
                    {log.target_id && (
                      <span className="font-mono text-[10px] text-slate-500 block">
                        {log.target_id.substring(0, 8)}...
                      </span>
                    )}
                  </td>
                  <td className="p-3 max-w-xs">
                    {log.payload ? (
                      <div className="space-y-1 font-mono text-[10px] text-slate-400 leading-relaxed">
                        {(log.payload as any).before && (
                          <p>
                            <span className="text-rose-400/80">Before:</span>{' '}
                            {JSON.stringify((log.payload as any).before)}
                          </p>
                        )}
                        {(log.payload as any).after && (
                          <p>
                            <span className="text-emerald-400/80">After:</span>{' '}
                            {JSON.stringify((log.payload as any).after)}
                          </p>
                        )}
                        {(log.payload as any).reason && (
                          <p className="italic text-indigo-300">
                            Reason: "{(log.payload as any).reason}"
                          </p>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-500 italic">No diff data</span>
                    )}
                  </td>
                  <td className="p-3 text-slate-400">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="p-3 text-right font-mono text-slate-500">{log.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

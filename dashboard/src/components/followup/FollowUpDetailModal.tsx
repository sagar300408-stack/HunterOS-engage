import React, { useState, useEffect } from 'react'
import { fetchFollowUpDetail, updateFollowUpMessage, rescheduleFollowUp, pauseFollowUp, resumeFollowUp, cancelFollowUp, sendFollowUpNow } from '../../api/followup'
import type { FollowUpQueueDetail } from '../../types'
import { X, Save, Edit2, Play, Pause, Trash2, Shield, Calendar, FastForward } from 'lucide-react'

export default function FollowUpDetailModal({ id, onClose, onRefresh }: { id: string, onClose: () => void, onRefresh: () => void }) {
  const [detail, setDetail] = useState<FollowUpQueueDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [editingMsg, setEditingMsg] = useState(false)
  const [msgDraft, setMsgDraft] = useState('')
  const [saving, setSaving] = useState(false)

  const loadData = () => {
    setLoading(true)
    fetchFollowUpDetail(id).then(d => {
      setDetail(d)
      setMsgDraft(d.final_message || d.generated_message || '')
      setLoading(false)
    })
  }

  useEffect(() => {
    loadData()
  }, [id])

  if (loading) return <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"><div className="card w-[600px] h-[400px] skeleton"></div></div>
  if (!detail) return null

  const handleSaveMsg = async () => {
    setSaving(true)
    await updateFollowUpMessage(id, msgDraft)
    setEditingMsg(false)
    setSaving(false)
    loadData()
    onRefresh()
  }

  const handleAction = async (action: 'pause' | 'resume' | 'cancel' | 'send') => {
    setSaving(true)
    if (action === 'pause') await pauseFollowUp(id)
    if (action === 'resume') await resumeFollowUp(id)
    if (action === 'cancel') await cancelFollowUp(id, 'Manual cancellation')
    if (action === 'send') await sendFollowUpNow(id)
    setSaving(false)
    loadData()
    onRefresh()
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center backdrop-blur-sm p-4">
      <div className="bg-[#0f172a] rounded-xl border border-slate-700 w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
        <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/30">
          <div>
            <h2 className="font-bold text-lg text-slate-100 flex items-center gap-2">
              Strategy: {detail.strategy?.replace('_', ' ')}
            </h2>
            <p className="text-xs text-slate-400">For {detail.customer_name} ({detail.customer_phone})</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-700/50 rounded-full transition-colors"><X className="h-5 w-5" /></button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-6">
            <div className="card p-4 bg-slate-800/20">
              <div className="flex justify-between items-center mb-3">
                <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 block">Message Preview</span>
                {detail.status === 'scheduled' && !editingMsg && (
                  <button onClick={() => setEditingMsg(true)} className="text-xs flex items-center gap-1 text-indigo-400 hover:text-indigo-300">
                    <Edit2 className="h-3 w-3" /> Edit
                  </button>
                )}
              </div>
              
              {editingMsg ? (
                <div className="space-y-2">
                  <textarea 
                    value={msgDraft} 
                    onChange={e => setMsgDraft(e.target.value)} 
                    className="w-full bg-[#0f172a] border border-slate-700 rounded-lg p-3 text-sm min-h-[150px] focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setEditingMsg(false)} className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200">Cancel</button>
                    <button onClick={handleSaveMsg} disabled={saving} className="btn-primary py-1.5 px-3 text-xs flex items-center gap-1">
                      <Save className="h-3 w-3" /> {saving ? 'Saving...' : 'Save Override'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-[#0f172a] p-4 rounded-lg border border-slate-700/50 text-sm whitespace-pre-wrap text-slate-300">
                  {detail.final_message || detail.generated_message || 'No message generated.'}
                </div>
              )}
            </div>

            <div className="card p-4">
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 block mb-3">Execution Controls</span>
              <div className="flex flex-wrap gap-2">
                {detail.status === 'scheduled' && (
                  <>
                    {!detail.human_paused ? (
                      <button onClick={() => handleAction('pause')} disabled={saving} className="btn flex items-center gap-1.5 bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20 text-xs py-1.5 px-3">
                        <Pause className="h-3.5 w-3.5" /> Pause
                      </button>
                    ) : (
                      <button onClick={() => handleAction('resume')} disabled={saving} className="btn flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20 text-xs py-1.5 px-3">
                        <Play className="h-3.5 w-3.5" /> Resume
                      </button>
                    )}
                    <button onClick={() => handleAction('send')} disabled={saving} className="btn flex items-center gap-1.5 bg-indigo-500/10 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/20 text-xs py-1.5 px-3">
                      <FastForward className="h-3.5 w-3.5" /> Send Now
                    </button>
                    <button onClick={() => handleAction('cancel')} disabled={saving} className="btn flex items-center gap-1.5 bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20 text-xs py-1.5 px-3">
                      <Trash2 className="h-3.5 w-3.5" /> Cancel
                    </button>
                  </>
                )}
                {detail.status !== 'scheduled' && (
                  <div className="text-xs text-slate-500 italic">No manual controls available in '{detail.status}' state.</div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="card p-4">
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 block mb-3 flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5 text-indigo-400" /> AI Explainability Report
              </span>
              
              {detail.explainability_report ? (
                <div className="space-y-4 text-sm">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold block">Decision Reason</span>
                    <span className="text-slate-300">{detail.explainability_report.decision_reason}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 font-semibold block">Policy Applied</span>
                    <span className="badge bg-indigo-500/10 text-indigo-400 border-indigo-500/20 mt-1">{detail.explainability_report.policy_applied}</span>
                  </div>
                  {detail.explainability_report.strategy_instructions && (
                    <div>
                      <span className="text-xs text-slate-500 font-semibold block">Strategy Instructions</span>
                      <span className="text-slate-300 italic">"{detail.explainability_report.strategy_instructions}"</span>
                    </div>
                  )}
                  <div>
                    <span className="text-xs text-slate-500 font-semibold block mb-1">Factors Considered</span>
                    <pre className="bg-[#0f172a] p-3 rounded-lg border border-slate-800 text-[10px] overflow-x-auto text-slate-400 font-mono">
                      {JSON.stringify(detail.explainability_report.factors_considered, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-500 italic text-center py-8">No explainability report available.</div>
              )}
            </div>
            
            <div className="card p-4">
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 block mb-3 flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-400" /> Timeline
              </span>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between border-b border-slate-700/50 pb-2">
                  <span className="text-slate-400">Created</span>
                  <span className="text-slate-200">{new Date(detail.created_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between border-b border-slate-700/50 pb-2">
                  <span className="text-slate-400">Scheduled For</span>
                  <span className="text-indigo-400 font-bold">{new Date(detail.scheduled_for).toLocaleString()}</span>
                </div>
                {detail.executed_at && (
                  <div className="flex justify-between pb-1">
                    <span className="text-slate-400">Executed</span>
                    <span className="text-emerald-400 font-bold">{new Date(detail.executed_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

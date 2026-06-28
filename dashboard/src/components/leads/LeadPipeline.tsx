import React, { useState } from 'react'
import { Kanban, Calendar, Clock, AlertTriangle, ArrowRight, CornerDownRight } from 'lucide-react'
import type { LeadPipeline as PipelineType, LeadCard } from '../../types'

interface LeadPipelineProps {
  pipeline: PipelineType | undefined
  loading: boolean
  onMoveLead: (customerId: string, newStage: string, reason?: string) => void
}

export const LeadPipeline: React.FC<LeadPipelineProps> = ({ pipeline, loading, onMoveLead }) => {
  const [draggingId, setDraggingId] = useState<string | null>(null)

  const columns = [
    { key: 'Research', label: 'Research / Cold', color: 'border-t-slate-500 bg-slate-900/10' },
    { key: 'Comparing Options', label: 'Comparing Options', color: 'border-t-cyan-500 bg-cyan-900/5' },
    { key: 'Ready to Schedule', label: 'Ready to Schedule', color: 'border-t-emerald-500 bg-emerald-900/5' },
    { key: 'Negotiation', label: 'Negotiation', color: 'border-t-purple-500 bg-purple-900/5' },
    { key: 'Purchase Ready', label: 'Purchase Ready', color: 'border-t-rose-500 bg-rose-900/5' },
  ]

  const handleDragStart = (e: React.DragEvent, id: string) => {
    e.dataTransfer.setData('text/plain', id)
    setDraggingId(id)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault() // Required to allow dropping
  }

  const handleDrop = (e: React.DragEvent, targetStage: string) => {
    e.preventDefault()
    const id = e.dataTransfer.getData('text/plain')
    setDraggingId(null)
    if (id) {
      const reason = prompt(`Reason for moving lead to "${targetStage}":`) || 'Manual operator drag-and-drop'
      onMoveLead(id, targetStage, reason)
    }
  }

  const getUrgencyBadge = (urgency: string | undefined) => {
    switch (urgency?.toLowerCase()) {
      case 'high':
        return 'text-rose-400 bg-rose-500/10 border border-rose-500/15'
      case 'medium':
        return 'text-amber-400 bg-amber-500/10 border border-amber-500/15'
      case 'low':
      default:
        return 'text-slate-400 bg-slate-500/10 border border-slate-500/15'
    }
  }

  if (loading) {
    return <div className="card h-128 skeleton"></div>
  }

  return (
    <div className="card space-y-6">
      <div className="flex items-center gap-2">
        <Kanban className="h-5 w-5 text-indigo-400" />
        <div>
          <h2 className="text-base font-bold text-slate-200">Interactive Lead Pipeline</h2>
          <p className="text-xs text-slate-400 mt-1">Drag and drop cards between stages to trigger CRM orchestration</p>
        </div>
      </div>

      {/* Horizontal Scroll Columns */}
      <div className="flex gap-4 overflow-x-auto pb-4 min-h-[500px]">
        {columns.map((col) => {
          const cards = pipeline?.stages[col.key] || []
          return (
            <div
              key={col.key}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, col.key)}
              className={`w-72 rounded-xl border border-slate-700 border-t-4 flex flex-col p-3 gap-3 shrink-0 ${col.color}`}
            >
              {/* Header column */}
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-bold text-slate-300">{col.label}</span>
                <span className="text-xs font-mono font-bold bg-[#0f172a]/60 px-2 py-0.5 rounded text-slate-400 border border-slate-700">
                  {cards.length}
                </span>
              </div>

              {/* Cards Container */}
              <div className="flex-1 space-y-3 overflow-y-auto max-h-[460px] pr-1">
                {cards.length === 0 ? (
                  <div className="text-center py-12 text-slate-600 border border-dashed border-slate-800 rounded-xl text-xs">
                    Drop leads here
                  </div>
                ) : (
                  cards.map((card) => (
                    <div
                      key={card.customer_id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, card.customer_id)}
                      className={`p-3 bg-[#1e293b] border rounded-xl shadow cursor-grab active:cursor-grabbing hover:border-slate-500 transition-all flex flex-col gap-2 relative group ${
                        draggingId === card.customer_id ? 'opacity-40' : ''
                      }`}
                    >
                      {/* Grade Badge */}
                      <span className="absolute top-2.5 right-2.5 font-mono text-xs font-extrabold text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/10">
                        {card.qualification_grade}
                      </span>

                      {/* Customer Info */}
                      <div>
                        <h4 className="text-xs font-bold text-slate-200 truncate pr-6">
                          {card.name || 'Unnamed Profile'}
                        </h4>
                        <span className="text-[10px] text-slate-500 font-mono block mt-0.5">
                          {card.phone}
                        </span>
                      </div>

                      {/* Captured Entities */}
                      {(card.budget || card.interest) && (
                        <div className="space-y-1 mt-1 pt-2 border-t border-slate-800 text-[10px] text-slate-400">
                          {card.budget && (
                            <p className="truncate">
                              <span className="text-slate-500">Budget:</span> {card.budget}
                            </p>
                          )}
                          {card.interest && (
                            <p className="truncate">
                              <span className="text-slate-500">Property:</span> {card.interest}
                            </p>
                          )}
                        </div>
                      )}

                      {/* Urgency + score */}
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800">
                        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${getUrgencyBadge(card.urgency)}`}>
                          {card.urgency || 'low'}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono font-semibold">
                          Score: {card.qualification_score}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

import React, { useState } from 'react'
import { RotateCcw, Brain, Calendar, Info, Clock, CheckCircle } from 'lucide-react'
import { ExplainabilityModal } from '../intent/ExplainabilityModal'
import { EventReplayPlayer } from '../activity/EventReplayPlayer'
import type { ConversationDetail, MessageDetail, IntentSummary } from '../../types'

interface ConversationViewerProps {
  convo: ConversationDetail | undefined
  loading: boolean
}

export const ConversationViewer: React.FC<ConversationViewerProps> = ({ convo, loading }) => {
  const [selectedIntent, setSelectedIntent] = useState<IntentSummary | null>(null)
  const [showReplay, setShowReplay] = useState(false)

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-[#1e293b]/10 justify-between">
        <div className="p-4 border-b border-[#334155] skeleton h-16"></div>
        <div className="flex-1 p-6 space-y-4 overflow-y-auto">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className={`flex ${i % 2 === 0 ? 'justify-start' : 'justify-end'}`}
            >
              <div className="w-1/2 h-20 skeleton"></div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-[#334155] skeleton h-16"></div>
      </div>
    )
  }

  if (!convo) {
    return (
      <div className="flex flex-col h-full items-center justify-center bg-[#1e293b]/10 text-slate-500 p-8 text-center">
        <Brain className="h-12 w-12 text-slate-700 mb-3" />
        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Select a Conversation</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          Select an ongoing chat thread from the left feed to inspect message trails, AI logs, and replay traces.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-[#1e293b]/10">
      {/* Detail Header */}
      <div className="px-6 py-4 border-b border-[#334155] bg-[#1e293b]/50 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-200">
            {convo.customer_name || convo.customer_phone}
          </h2>
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-0.5">
            <span className="font-mono">{convo.customer_phone}</span>
            <span className="text-slate-600">•</span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              Started {new Date(convo.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Replay controller */}
        {convo.pipeline_events && convo.pipeline_events.length > 0 && (
          <button
            onClick={() => setShowReplay(true)}
            className="btn-ghost flex items-center gap-1.5 px-3 py-1.5 text-xs border border-slate-700 bg-slate-800/40 hover:bg-slate-800"
          >
            <RotateCcw className="h-3.5 w-3.5 text-indigo-400" />
            Replay Pipeline
          </button>
        )}
      </div>

      {/* Bubble Chat Streams */}
      <div className="flex-1 p-6 space-y-6 overflow-y-auto bg-[#0f172a]/20">
        {convo.messages.map((msg) => {
          const isAI = msg.direction === 'outgoing'
          return (
            <div key={msg.id} className={`flex ${isAI ? 'justify-end' : 'justify-start'} w-full fade-in`}>
              <div className={`max-w-[70%] group`}>
                
                {/* Bubble Container */}
                <div
                  className={`p-4 rounded-xl border text-sm leading-relaxed ${
                    isAI
                      ? 'bg-indigo-500/10 border-indigo-500/20 text-slate-200'
                      : 'bg-[#1e293b]/80 border-slate-700/60 text-slate-300'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Attachment metadata metrics on AI replies */}
                  {isAI && (msg.total_tokens || msg.estimated_cost_usd) && (
                    <div className="mt-3 pt-2.5 border-t border-indigo-500/10 flex flex-wrap items-center gap-3 text-[10px] text-slate-400 font-mono">
                      {msg.ai_model && <span>Model: {msg.ai_model}</span>}
                      {msg.total_tokens && <span>Tokens: {msg.total_tokens}</span>}
                      {msg.latency_ms && (
                        <span className="flex items-center gap-0.5">
                          <Clock className="h-3 w-3" />
                          {msg.latency_ms} ms
                        </span>
                      )}
                      {msg.estimated_cost_usd !== undefined && (
                        <span className="text-emerald-400 font-semibold">
                          ${Number(msg.estimated_cost_usd).toFixed(5)}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Intent tag overlay on customer messages */}
                  {!isAI && msg.intent && (
                    <div className="mt-3 pt-2.5 border-t border-slate-700/40 flex items-center justify-between text-[10px]">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-400 uppercase tracking-widest">Extracted Intent:</span>
                        <span className="font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/10">
                          {msg.intent.detected_intent}
                        </span>
                      </div>
                      <button
                        onClick={() => setSelectedIntent(msg.intent ?? null)}
                        className="text-slate-400 hover:text-slate-200 flex items-center gap-1 font-semibold cursor-pointer"
                      >
                        <Brain className="h-3.5 w-3.5 text-indigo-400" />
                        Explain
                      </button>
                    </div>
                  )}
                </div>

                {/* Sub-label timestamp */}
                <div className={`mt-1.5 flex items-center text-[10px] text-slate-500 px-1 ${isAI ? 'justify-end' : 'justify-start'}`}>
                  <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>

              </div>
            </div>
          )
        })}
      </div>

      {/* Explainability modal overlay */}
      {selectedIntent && (
        <ExplainabilityModal intent={selectedIntent} onClose={() => setSelectedIntent(null)} />
      )}

      {/* Replay event overlay */}
      {showReplay && convo.pipeline_events && (
        <EventReplayPlayer events={convo.pipeline_events} onClose={() => setShowReplay(false)} />
      )}
    </div>
  )
}

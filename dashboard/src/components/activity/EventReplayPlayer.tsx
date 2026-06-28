import React, { useState, useEffect } from 'react'
import { Play, Pause, RotateCcw, X, CheckCircle2, AlertCircle, Clock } from 'lucide-react'
import type { PipelineEvent } from '../../types'

interface EventReplayPlayerProps {
  events: PipelineEvent[]
  onClose: () => void
}

export const EventReplayPlayer: React.FC<EventReplayPlayerProps> = ({ events, onClose }) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(-1)
  const [speed, setSpeed] = useState(1000) // ms delay between steps

  const steps = [
    { key: 'message_received', label: 'Message Received' },
    { key: 'customer_identified', label: 'Customer Identified' },
    { key: 'memory_loaded', label: 'Memory Loaded' },
    { key: 'intent_extracted', label: 'Intent Extracted' },
    { key: 'response_generated', label: 'Response Generated' },
    { key: 'memory_updated', label: 'Memory Updated' },
    { key: 'reply_sent', label: 'Reply Sent' },
  ]

  // Filter events matching the predefined steps
  const eventMap = new Map<string, PipelineEvent>()
  events.forEach((ev) => {
    eventMap.set(ev.step, ev)
  })

  useEffect(() => {
    let timer: any
    if (isPlaying) {
      if (currentIndex < steps.length - 1) {
        timer = setTimeout(() => {
          setCurrentIndex((prev) => prev + 1)
        }, speed)
      } else {
        setIsPlaying(false)
      }
    }
    return () => clearTimeout(timer)
  }, [isPlaying, currentIndex, speed])

  const handleStart = () => {
    if (currentIndex === steps.length - 1) {
      setCurrentIndex(0)
    } else if (currentIndex === -1) {
      setCurrentIndex(0)
    }
    setIsPlaying(true)
  }

  const handleReset = () => {
    setIsPlaying(false)
    setCurrentIndex(-1)
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="w-full max-w-2xl bg-[#1e293b] border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-150">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-700/60 flex items-center justify-between bg-[#0f172a]/30">
          <div className="flex items-center gap-2 text-indigo-400">
            <RotateCcw className="h-5 w-5" />
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Pipeline Event Replay Trace</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 cursor-pointer">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Player Controls */}
        <div className="p-4 bg-[#0f172a]/40 border-b border-slate-700/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={isPlaying ? () => setIsPlaying(false) : handleStart}
              className="btn-primary flex items-center gap-1.5 px-4 py-2 text-xs"
            >
              {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              {isPlaying ? 'Pause' : 'Play Replay'}
            </button>
            <button
              onClick={handleReset}
              className="btn-ghost flex items-center gap-1.5 px-3 py-2 text-xs"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </button>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <span className="text-slate-400">Delay:</span>
            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="input py-1 text-xs w-24 bg-[#1e293b]"
            >
              <option value={1500}>1.5s (Slow)</option>
              <option value={1000}>1.0s (Normal)</option>
              <option value={500}>0.5s (Fast)</option>
            </select>
          </div>
        </div>

        {/* Timeline body */}
        <div className="p-6 space-y-6">
          <div className="relative pl-8 space-y-6 before:absolute before:inset-y-1 before:left-[11px] before:w-0.5 before:bg-slate-700">
            {steps.map((step, idx) => {
              const active = idx === currentIndex
              const completed = idx < currentIndex
              const loggedEvent = eventMap.get(step.key)
              
              // Status of step
              let nodeColor = 'bg-slate-800 border-slate-700 text-slate-500'
              if (active) {
                nodeColor = 'bg-indigo-500/20 border-indigo-400 text-indigo-400 pulse-green'
              } else if (completed) {
                nodeColor = loggedEvent?.status === 'error'
                  ? 'bg-rose-500/25 border-rose-500 text-rose-400'
                  : 'bg-emerald-500/25 border-emerald-500 text-emerald-400'
              }

              return (
                <div key={step.key} className={`relative transition-all duration-200 ${active ? 'scale-[1.01]' : ''}`}>
                  {/* Node Circle indicator */}
                  <span className={`absolute -left-[28px] top-1 h-6.5 w-6.5 rounded-full border-2 flex items-center justify-center text-[10px] font-bold z-10 ${nodeColor}`}>
                    {idx + 1}
                  </span>

                  <div className={`p-4 rounded-xl border transition-all ${
                    active 
                      ? 'border-indigo-500/40 bg-indigo-500/5 shadow-md shadow-indigo-500/5' 
                      : 'border-slate-800 bg-[#1e293b]/20'
                  }`}>
                    <div className="flex justify-between items-center">
                      <span className={`text-sm font-bold ${active ? 'text-indigo-400' : 'text-slate-300'}`}>
                        {step.label}
                      </span>
                      {completed && loggedEvent && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                          {loggedEvent.duration_ms !== undefined && (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {loggedEvent.duration_ms} ms
                            </span>
                          )}
                          {loggedEvent.status === 'error' ? (
                            <AlertCircle className="h-4 w-4 text-rose-400" />
                          ) : (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          )}
                        </div>
                      )}
                    </div>

                    {/* Step Snapshot Data when active/completed */}
                    {(active || completed) && loggedEvent && (
                      <div className="mt-3 bg-[#0f172a]/50 rounded-lg p-3 border border-slate-700/50 font-mono text-[10px] text-slate-400 overflow-x-auto max-h-40">
                        {step.key === 'message_received' && loggedEvent.payload && (
                          <div className="space-y-1">
                            <p><span className="text-indigo-400">Content:</span> "{(loggedEvent.payload as any).content}"</p>
                            <p><span className="text-indigo-400">From:</span> {(loggedEvent.payload as any).from_phone}</p>
                          </div>
                        )}
                        {step.key === 'intent_extracted' && loggedEvent.payload && (
                          <div className="space-y-1">
                            <p><span className="text-indigo-400">Intent:</span> {(loggedEvent.payload as any).intent}</p>
                            <p><span className="text-indigo-400">Confidence:</span> {Math.round(Number((loggedEvent.payload as any).confidence) * 100)}%</p>
                            <p><span className="text-indigo-400">Urgency:</span> {(loggedEvent.payload as any).urgency}</p>
                          </div>
                        )}
                        {step.key === 'response_generated' && loggedEvent.payload && (
                          <div className="space-y-1">
                            <p><span className="text-indigo-400">Response:</span> "{(loggedEvent.payload as any).response}"</p>
                          </div>
                        )}
                        {step.key === 'memory_updated' && loggedEvent.payload && (
                          <div className="space-y-1">
                            <p><span className="text-indigo-400">Summary:</span> "{(loggedEvent.payload as any).summary || (loggedEvent.payload as any).current_summary}"</p>
                          </div>
                        )}
                        {!['message_received', 'intent_extracted', 'response_generated', 'memory_updated'].includes(step.key) && (
                          <pre>{JSON.stringify(loggedEvent.payload, null, 2)}</pre>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

      </div>
    </div>
  )
}

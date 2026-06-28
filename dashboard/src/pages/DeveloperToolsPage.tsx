import React, { useState, useEffect } from 'react'
import {
  Sliders,
  Play,
  Send,
  Calendar,
  RefreshCw,
  Trash2,
  CheckCircle,
  XCircle,
  FileCode,
  Gauge,
  Flame,
  Clock,
  Settings,
  Database,
  Terminal,
} from 'lucide-react'

export const DeveloperToolsPage = () => {
  // Tab control
  const [activeTab, setActiveTab] = useState<'control' | 'scenarios' | 'timeline' | 'regression' | 'reset'>('control')

  // Status and values
  const [simState, setSimState] = useState({
    openai_status: 'online',
    database_status: 'online',
    whatsapp_status: 'online',
    redis_status: 'online',
    email_status: 'online',
    worker_status: 'online',
    queue_status: 'online',
    latency_ms: 0,
    mock_ai: true,
    mock_whatsapp: true,
    time_offset_seconds: 0,
  })

  const [metrics, setMetrics] = useState({
    cpu_usage_pct: 0,
    ram_usage_pct: 0,
    db_latency_ms: 0,
    avg_api_latency_ms: 0,
    total_token_usage: 0,
    avg_token_usage_per_response: 0,
    websocket_throughput: 0,
  })

  // Timeline
  const [timeline, setTimeline] = useState<any[]>([])
  const [replayJson, setReplayJson] = useState('')

  // Regression results
  const [regression, setRegression] = useState<any>(null)
  const [runningTests, setRunningTests] = useState(false)

  // Webhook Simulator form
  const [webhookForm, setWebhookForm] = useState({
    channel: 'WhatsApp',
    contact_name: 'Jane Doe',
    identifier: '12025550188',
    message: 'Hello, looking to see properties in Downtown.',
  })

  // Job Generator form
  const [jobForm, setJobForm] = useState({
    job_type: 'crm_sync',
    count: 5,
  })

  // Time travel form
  const [travelSeconds, setTravelSeconds] = useState(3600) // 1 hour default

  // Reset options
  const [resetOptions, setResetOptions] = useState({
    clear_conversations: false,
    clear_buyers: false,
    clear_activity: false,
    clear_queue: false,
    clear_audit_logs: false,
    reset_everything: false,
  })

  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // Load config & metrics on mount
  useEffect(() => {
    fetchConfig()
    fetchDiagnostics()
    fetchTimeline()
  }, [])

  const showMessage = (text: string, type: 'success' | 'error' = 'success') => {
    setMessage({ text, type })
    setTimeout(() => setMessage(null), 5000)
  }

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/v1/developer-tools/config')
      if (res.ok) {
        const data = await res.json()
        setSimState(data)
      }
    } catch (err) {
      console.error('Failed to load simulation configuration', err)
    }
  }

  const fetchDiagnostics = async () => {
    try {
      const res = await fetch('/api/v1/developer-tools/metrics')
      if (res.ok) {
        const data = await res.json()
        setMetrics(data)
      }
    } catch (err) {
      console.error('Failed to load diagnostics', err)
    }
  }

  const fetchTimeline = async () => {
    try {
      const res = await fetch('/api/v1/developer-tools/timeline')
      if (res.ok) {
        const data = await res.json()
        setTimeline(data)
      }
    } catch (err) {
      console.error('Failed to load timeline logs', err)
    }
  }

  const handleToggleState = async (updates: Partial<typeof simState>) => {
    try {
      const res = await fetch('/api/v1/developer-tools/simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (res.ok) {
        const data = await res.json()
        setSimState(data)
        showMessage('Simulation state updated.')
        fetchTimeline()
      }
    } catch (err) {
      showMessage('Failed to update state.', 'error')
    }
  }

  const handleTriggerScenario = async (scenarioName: string) => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/developer-tools/trigger-scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_name: scenarioName }),
      })
      if (res.ok) {
        showMessage(`Scenario "${scenarioName}" triggered successfully!`)
        fetchTimeline()
      } else {
        showMessage('Failed to execute scenario.', 'error')
      }
    } catch (err) {
      showMessage('Connection error.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleSimulateWebhook = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/developer-tools/webhook-simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(webhookForm),
      })
      if (res.ok) {
        showMessage('Webhook event simulated successfully!')
        fetchTimeline()
      } else {
        showMessage('Failed to simulate webhook.', 'error')
      }
    } catch (err) {
      showMessage('Connection error.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateJobs = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/developer-tools/generate-jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jobForm),
      })
      if (res.ok) {
        const data = await res.json()
        showMessage(`Successfully generated ${data.count} background tasks.`)
        fetchTimeline()
      } else {
        showMessage('Failed to generate background tasks.', 'error')
      }
    } catch (err) {
      showMessage('Connection error.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleTimeTravel = async (secondsToAdd: number) => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/developer-tools/time-travel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seconds: secondsToAdd }),
      })
      if (res.ok) {
        const data = await res.json()
        const count = data.time_travel_results.jobs_processed_count
        showMessage(`Travelled forward in time! Processed ${count} pending jobs.`)
        fetchConfig()
        fetchTimeline()
      } else {
        showMessage('Failed to advance clock.', 'error')
      }
    } catch (err) {
      showMessage('Connection error.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleClearTimeline = async () => {
    try {
      await fetch('/api/v1/developer-tools/timeline/clear', { method: 'POST' })
      setTimeline([])
      showMessage('Timeline logs cleared.')
    } catch (err) {}
  }

  const handleReplayTimeline = async () => {
    if (!replayJson.trim()) return
    setLoading(true)
    try {
      const parsed = JSON.parse(replayJson)
      const res = await fetch('/api/v1/developer-tools/timeline/replay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      })
      if (res.ok) {
        const data = await res.json()
        showMessage(`Replayed timeline! Executed ${data.replayed_steps} steps.`)
        setReplayJson('')
        fetchTimeline()
      } else {
        showMessage('Replay execution failed.', 'error')
      }
    } catch (err) {
      showMessage('Invalid JSON syntax.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleRunRegression = async () => {
    setRunningTests(true)
    try {
      const res = await fetch('/api/v1/developer-tools/run-tests', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setRegression(data)
        showMessage(data.success ? 'All regression tests passed!' : 'Regression failures encountered.', data.success ? 'success' : 'error')
      }
    } catch (err) {
      showMessage('Failed to execute regression suite.', 'error')
    } finally {
      setRunningTests(false)
    }
  }

  const handleResetData = async () => {
    const confirmed = window.confirm('Are you absolutely sure you want to delete these sandbox records? This is irreversible.')
    if (!confirmed) return

    setLoading(true)
    try {
      const res = await fetch('/api/v1/developer-tools/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(resetOptions),
      })
      if (res.ok) {
        const data = await res.json()
        showMessage('Data reset completed: ' + JSON.stringify(data.cleanup_results))
        fetchTimeline()
      }
    } catch (err) {
      showMessage('Reset failed.', 'error')
    } finally {
      setLoading(false)
    }
  }

  // Calculate current simulated time string
  const getSimulatedTime = () => {
    const base = new Date()
    return new Date(base.getTime() + simState.time_offset_seconds * 1000).toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Toast Alert Banner */}
      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-3 border shadow-lg slide-in fixed top-4 right-4 z-50 ${
          message.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
            : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
        }`}>
          {message.type === 'success' ? <CheckCircle className="h-5 w-5 shrink-0" /> : <XCircle className="h-5 w-5 shrink-0" />}
          <span className="text-xs font-semibold">{message.text}</span>
        </div>
      )}

      {/* Header Widget Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card bg-[#1e293b]/40 border border-slate-700/40 p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Time Machine Status</span>
            <p className="text-sm font-bold text-slate-200">{getSimulatedTime()}</p>
            <p className="text-[10px] text-slate-400">
              Offset: <span className="font-mono text-indigo-400">+{simState.time_offset_seconds}s</span>
            </p>
          </div>
          <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
            <Clock className="h-5 w-5" />
          </div>
        </div>

        <div className="card bg-[#1e293b]/40 border border-slate-700/40 p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Database Load Engine</span>
            <p className="text-sm font-bold text-slate-200">
              {simState.database_status === 'slow' ? 'Slow Mode (Artificial Delay)' : 'Normal'}
            </p>
            <p className="text-[10px] text-slate-400">
              Simulated latency: <span className="font-mono text-indigo-400">{metrics.db_latency_ms}ms</span>
            </p>
          </div>
          <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
            <Database className="h-5 w-5" />
          </div>
        </div>

        <div className="card bg-[#1e293b]/40 border border-slate-700/40 p-5 flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Simulators</span>
            <div className="flex gap-2.5 mt-1">
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${simState.mock_ai ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-slate-700/20 text-slate-500 border border-slate-700/40'}`}>
                Mock AI
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono ${simState.mock_whatsapp ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-slate-700/20 text-slate-500 border border-slate-700/40'}`}>
                Mock WhatsApp
              </span>
            </div>
          </div>
          <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
            <Settings className="h-5 w-5" />
          </div>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="border-b border-slate-800 flex gap-2">
        <button
          onClick={() => setActiveTab('control')}
          className={`px-4 py-2.5 border-b-2 text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'control' 
              ? 'border-indigo-500 text-indigo-400' 
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Outage & Middleware Control
        </button>
        <button
          onClick={() => setActiveTab('scenarios')}
          className={`px-4 py-2.5 border-b-2 text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'scenarios' 
              ? 'border-indigo-500 text-indigo-400' 
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Scenario & Webhook Simulator
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2.5 border-b-2 text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'timeline' 
              ? 'border-indigo-500 text-indigo-400' 
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Timeline Logs & Replay
        </button>
        <button
          onClick={() => setActiveTab('regression')}
          className={`px-4 py-2.5 border-b-2 text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'regression' 
              ? 'border-indigo-500 text-indigo-400' 
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Regression Suite
        </button>
        <button
          onClick={() => setActiveTab('reset')}
          className={`px-4 py-2.5 border-b-2 text-xs font-semibold transition-all cursor-pointer ${
            activeTab === 'reset' 
              ? 'border-indigo-500 text-indigo-400' 
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Sandbox Cleanup
        </button>
      </div>

      {/* Tab Panels */}
      <div className="space-y-6">
        {activeTab === 'control' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Outage Toggle Tweak panel */}
            <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-5 lg:col-span-2">
              <h2 className="text-sm font-bold text-slate-200">System Outages Controls</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-slate-400">OpenAI API Connection</label>
                  <select
                    value={simState.openai_status}
                    onChange={(e) => handleToggleState({ openai_status: e.target.value })}
                    className="w-full text-xs"
                  >
                    <option value="online">Online</option>
                    <option value="timeout">Artificial Timeout (10s delay)</option>
                    <option value="offline">Offline Outage (Throws exception)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">WhatsApp API Integration</label>
                  <select
                    value={simState.whatsapp_status}
                    onChange={(e) => handleToggleState({ whatsapp_status: e.target.value })}
                    className="w-full text-xs"
                  >
                    <option value="online">Online</option>
                    <option value="offline">Offline Outage</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Database Connection</label>
                  <select
                    value={simState.database_status}
                    onChange={(e) => handleToggleState({ database_status: e.target.value })}
                    className="w-full text-xs"
                  >
                    <option value="online">Online</option>
                    <option value="slow">Slow Mode (+2000ms delay)</option>
                    <option value="offline">Offline</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Queue & Task Workers</label>
                  <select
                    value={simState.worker_status}
                    onChange={(e) => handleToggleState({ worker_status: e.target.value })}
                    className="w-full text-xs"
                  >
                    <option value="online">Online (Active)</option>
                    <option value="offline">Offline Outage (Stops background jobs)</option>
                  </select>
                </div>
              </div>

              <div className="border-t border-slate-800 pt-4 space-y-4">
                <h3 className="text-xs font-bold text-slate-300">Artificial API Network Latency</h3>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="5000"
                    step="100"
                    value={simState.latency_ms}
                    onChange={(e) => handleToggleState({ latency_ms: parseInt(e.target.value) })}
                    className="flex-1"
                  />
                  <span className="text-xs font-mono text-slate-300 w-16 text-right shrink-0">
                    {simState.latency_ms} ms
                  </span>
                </div>
                <p className="text-[10px] text-slate-400">
                  Adds an artificial delay to all incoming API calls under /api/v1/ (excluding Developer Tools itself)
                </p>
              </div>

              <div className="border-t border-slate-800 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-3 rounded bg-slate-800/30 border border-slate-700/30">
                  <div>
                    <p className="text-xs font-semibold text-slate-200">Mock OpenAI Response</p>
                    <p className="text-[10px] text-slate-400">Circumvents OpenAI token expenses</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={simState.mock_ai}
                    onChange={(e) => handleToggleState({ mock_ai: e.target.checked })}
                    className="toggle-checkbox shrink-0"
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded bg-slate-800/30 border border-slate-700/30">
                  <div>
                    <p className="text-xs font-semibold text-slate-200">Mock WhatsApp Dispatch</p>
                    <p className="text-[10px] text-slate-400">Circumvents Meta outbound delivery</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={simState.mock_whatsapp}
                    onChange={(e) => handleToggleState({ mock_whatsapp: e.target.checked })}
                    className="toggle-checkbox shrink-0"
                  />
                </div>
              </div>
            </div>

            {/* Time Machine control panel */}
            <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-5 flex flex-col justify-between">
              <div className="space-y-4">
                <h2 className="text-sm font-bold text-slate-200">Time Machine Controls</h2>
                <p className="text-[10px] text-slate-400">
                  Travel forward in time to trigger follow-up schedules, test queue execution, or verify customer memory age thresholds.
                </p>
                
                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Skip Interval (Seconds)</label>
                  <input
                    type="number"
                    value={travelSeconds}
                    onChange={(e) => setTravelSeconds(parseInt(e.target.value) || 0)}
                    className="w-full text-xs text-slate-200 bg-slate-800/50 border-slate-700"
                  />
                </div>
              </div>

              <div className="space-y-3 mt-6">
                <button
                  disabled={loading}
                  onClick={() => handleTimeTravel(travelSeconds)}
                  className="btn-primary w-full flex items-center justify-center gap-1.5 py-2 cursor-pointer text-xs"
                >
                  <Clock className="h-3.5 w-3.5" />
                  Jump Clock
                </button>

                <div className="grid grid-cols-2 gap-2 text-center">
                  <button
                    disabled={loading}
                    onClick={() => handleTimeTravel(300)}
                    className="btn-secondary text-[10px] py-1.5 cursor-pointer"
                  >
                    +5 Minutes
                  </button>
                  <button
                    disabled={loading}
                    onClick={() => handleTimeTravel(3600)}
                    className="btn-secondary text-[10px] py-1.5 cursor-pointer"
                  >
                    +1 Hour
                  </button>
                  <button
                    disabled={loading}
                    onClick={() => handleTimeTravel(86400)}
                    className="btn-secondary text-[10px] py-1.5 cursor-pointer"
                  >
                    +1 Day
                  </button>
                  <button
                    disabled={loading}
                    onClick={() => handleTimeTravel(604800)}
                    className="btn-secondary text-[10px] py-1.5 cursor-pointer"
                  >
                    +1 Week
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'scenarios' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Scenarios triggers list */}
            <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-5 lg:col-span-2">
              <h2 className="text-sm font-bold text-slate-200">Simulate Real Estate Buyer Journeys</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { id: 'apartment_buyer', title: 'Sarah (Apartment Inq)', desc: '1-2 bed Downtown apartment under $350k.' },
                  { id: 'villa_buyer', title: 'Michael (Villa Inq)', desc: 'Luxury Palm Jumeirah 4-bed villa for $3.5M.' },
                  { id: 'commercial_buyer', title: 'Corporate Office Inq', desc: '5,000 sq ft office in Business Bay.' },
                  { id: 'budget_increase', title: 'Sarah (Budget Upgrade)', desc: 'Increase Sarah budget Downtown to $450k.' },
                  { id: 'site_visit', title: 'Michael (Site Visit Req)', desc: 'Request booking visit Palm Jumeirah.' },
                  { id: 'negotiation', title: 'Michael (Negotiation)', desc: 'Initiate offer down to $3.3M.' },
                  { id: 'booking_confirmed', title: 'Michael (Booking Conf)', desc: 'Confirm final property agreement.' },
                  { id: 'lost_lead', title: 'John Cold (Halts search)', desc: 'Unsubscribes from marketing listings.' },
                  { id: 'returning_buyer', title: 'Michael (New Search)', desc: 'Returns looking for Marina rentals.' },
                  { id: 'high_priority', title: 'Elon Cash (Urgent)', desc: 'Cash Penthouse buy request for $15M.' },
                ].map((item) => (
                  <div key={item.id} className="p-4 rounded border border-slate-800 bg-[#1e293b]/40 flex justify-between items-start gap-4">
                    <div className="space-y-1">
                      <p className="text-xs font-bold text-slate-200">{item.title}</p>
                      <p className="text-[10px] text-slate-400 leading-normal">{item.desc}</p>
                    </div>
                    <button
                      disabled={loading}
                      onClick={() => handleTriggerScenario(item.id)}
                      className="p-2 rounded bg-indigo-500/10 hover:bg-indigo-500 text-indigo-400 hover:text-white border border-indigo-500/20 transition-all shrink-0 cursor-pointer"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Custom Webhook simulator */}
            <div className="space-y-6">
              <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-4">
                <h2 className="text-sm font-bold text-slate-200">Custom Webhook Simulator</h2>
                
                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Sender Channel</label>
                  <select
                    value={webhookForm.channel}
                    onChange={(e) => setWebhookForm({ ...webhookForm, channel: e.target.value })}
                    className="w-full text-xs"
                  >
                    <option value="WhatsApp">WhatsApp Message</option>
                    <option value="Website">Website Chat widget</option>
                    <option value="Email">Email Inquiry</option>
                    <option value="Instagram">Instagram Direct message</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Contact Full Name</label>
                  <input
                    type="text"
                    value={webhookForm.contact_name}
                    onChange={(e) => setWebhookForm({ ...webhookForm, contact_name: e.target.value })}
                    className="w-full text-xs bg-slate-800/50 border-slate-700 text-slate-200"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Identifier (Phone/Email)</label>
                  <input
                    type="text"
                    value={webhookForm.identifier}
                    onChange={(e) => setWebhookForm({ ...webhookForm, identifier: e.target.value })}
                    className="w-full text-xs bg-slate-800/50 border-slate-700 text-slate-200 font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Message Content</label>
                  <textarea
                    rows={3}
                    value={webhookForm.message}
                    onChange={(e) => setWebhookForm({ ...webhookForm, message: e.target.value })}
                    className="w-full text-xs bg-slate-800/50 border-slate-700 text-slate-200"
                  ></textarea>
                </div>

                <button
                  disabled={loading}
                  onClick={handleSimulateWebhook}
                  className="btn-primary w-full flex items-center justify-center gap-1.5 py-2 mt-4 cursor-pointer text-xs"
                >
                  <Send className="h-3.5 w-3.5" />
                  Simulate Event
                </button>
              </div>

              {/* Background job generator */}
              <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-4">
                <h2 className="text-sm font-bold text-slate-200">Queue Background Job Spawner</h2>
                
                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Job Type</label>
                  <select
                    value={jobForm.job_type}
                    onChange={(e) => setJobForm({ ...jobForm, job_type: e.target.value })}
                    className="w-full text-xs"
                  >
                    <option value="crm_sync">CRM Sync Task</option>
                    <option value="followup_schedule">Follow-up Scheduler</option>
                    <option value="memory_update">Memory Consolidation</option>
                    <option value="email">Email Sender</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Count</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={jobForm.count}
                    onChange={(e) => setJobForm({ ...jobForm, count: parseInt(e.target.value) || 1 })}
                    className="w-full text-xs bg-slate-800/50 border-slate-700 text-slate-200"
                  />
                </div>

                <button
                  disabled={loading}
                  onClick={handleGenerateJobs}
                  className="btn-secondary w-full flex items-center justify-center gap-1.5 py-2 cursor-pointer text-xs"
                >
                  <Gauge className="h-3.5 w-3.5 text-amber-500" />
                  Generate Jobs
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'timeline' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Timeline Trace list */}
            <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-5 lg:col-span-2">
              <div className="flex justify-between items-center">
                <h2 className="text-sm font-bold text-slate-200">Timeline Traces Log</h2>
                <div className="flex gap-2">
                  <button
                    onClick={fetchTimeline}
                    className="btn-ghost flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer"
                  >
                    <RefreshCw className="h-3 w-3" /> Refresh
                  </button>
                  <button
                    onClick={handleClearTimeline}
                    className="btn-ghost flex items-center gap-1 text-[10px] text-rose-400 hover:text-rose-300 cursor-pointer"
                  >
                    <Trash2 className="h-3 w-3" /> Clear
                  </button>
                </div>
              </div>

              <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                {timeline.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 text-xs border border-dashed border-slate-800 rounded">
                    No timeline logs captured. Execute a scenario, webhook simulation, or time jump to start recording.
                  </div>
                ) : (
                  timeline.map((evt, idx) => (
                    <div key={idx} className="p-3.5 rounded border border-slate-800/50 bg-[#1e293b]/30 flex flex-col gap-2 text-[11px] leading-relaxed">
                      <div className="flex justify-between items-center">
                        <span className="font-mono text-[10px] text-slate-500">
                          {new Date(evt.timestamp).toLocaleString()}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[9px] font-mono uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {evt.type}
                        </span>
                      </div>
                      <div className="space-y-1">
                        {evt.name && (
                          <p className="font-semibold text-slate-200">
                            Customer: {evt.name} <span className="font-mono text-slate-400">({evt.phone || evt.identifier})</span>
                          </p>
                        )}
                        {evt.message && (
                          <p className="text-slate-300 italic font-serif">
                            "{evt.message}"
                          </p>
                        )}
                        {evt.details && (
                          <p className="text-slate-400">
                            {evt.details}
                          </p>
                        )}
                        {evt.event && (
                          <p className="text-indigo-400 font-mono font-bold">
                            Event: {evt.event}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Replay JSON timeline panel */}
            <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-4 flex flex-col justify-between h-full">
              <div className="space-y-4">
                <h2 className="text-sm font-bold text-slate-200">Timeline Exporter & Replayer</h2>
                <p className="text-[10px] text-slate-400 leading-normal">
                  Export your captured scenario path or upload a previously captured JSON log to replicate the sequence of events.
                </p>
                
                <div className="space-y-2">
                  <button
                    onClick={() => {
                      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ scenario_name: "Exported Path", timeline }, null, 2))
                      const downloadAnchor = document.createElement('a')
                      downloadAnchor.setAttribute("href", dataStr)
                      downloadAnchor.setAttribute("download", `timeline_export_${Date.now()}.json`)
                      document.body.appendChild(downloadAnchor)
                      downloadAnchor.click()
                      downloadAnchor.remove()
                    }}
                    className="btn-secondary w-full py-1.5 text-xs flex items-center justify-center gap-1 cursor-pointer"
                  >
                    <FileCode className="h-3.5 w-3.5 text-indigo-400" />
                    Export Trace JSON
                  </button>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Paste Trace Logs JSON</label>
                  <textarea
                    rows={10}
                    value={replayJson}
                    onChange={(e) => setReplayJson(e.target.value)}
                    placeholder='{"scenario_name": "Sarah Journey", "timeline": [...] }'
                    className="w-full text-xs font-mono bg-slate-900 border-slate-700 text-slate-200 placeholder-slate-600"
                  ></textarea>
                </div>
              </div>

              <button
                disabled={loading || !replayJson}
                onClick={handleReplayTimeline}
                className="btn-primary w-full flex items-center justify-center gap-1.5 py-2 mt-4 cursor-pointer text-xs"
              >
                <Terminal className="h-3.5 w-3.5 text-indigo-400" />
                Upload & Replay
              </button>
            </div>
          </div>
        )}

        {activeTab === 'regression' && (
          <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-6">
            <div className="flex justify-between items-center border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <h2 className="text-sm font-bold text-slate-200">Regression Tests Runner</h2>
                <p className="text-[10px] text-slate-400">
                  Executes the complete test suite against local PostgreSQL and compares DB state assertions (intents, stage changes, memory).
                </p>
              </div>
              <button
                disabled={runningTests}
                onClick={handleRunRegression}
                className="btn-primary flex items-center gap-1.5 px-4 py-2 cursor-pointer text-xs"
              >
                <Flame className={`h-4 w-4 ${runningTests ? 'animate-pulse text-amber-500' : 'text-amber-400'}`} />
                {runningTests ? 'Running Regression...' : 'Run Regression Suite'}
              </button>
            </div>

            {regression ? (
              <div className="space-y-6">
                {/* Result Overview card */}
                <div className={`p-5 rounded-lg border flex items-center justify-between ${
                  regression.success 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                }`}>
                  <div className="space-y-1">
                    <p className="text-sm font-bold">{regression.success ? 'Regression Passed' : 'Regression Failed'}</p>
                    <p className="text-xs opacity-80">
                      Executed at {new Date(regression.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-6 font-mono text-xs">
                    <div className="text-center">
                      <p className="text-[10px] uppercase opacity-75">PASSED</p>
                      <p className="text-lg font-bold text-emerald-400">{regression.summary.total_passed}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] uppercase opacity-75">FAILED</p>
                      <p className="text-lg font-bold text-rose-400">{regression.summary.total_failed}</p>
                    </div>
                  </div>
                </div>

                {/* Categories breakdown list */}
                <div className="space-y-4">
                  {regression.results.map((cat: any, cidx: number) => (
                    <div key={cidx} className="p-4 rounded border border-slate-800 bg-[#1e293b]/40 space-y-3">
                      <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                        <h3 className="text-xs font-bold text-slate-300">{cat.category}</h3>
                        <span className="text-[10px] text-slate-400">
                          {cat.passed} Pass / {cat.failed} Fail
                        </span>
                      </div>

                      <div className="space-y-2">
                        {cat.test_cases.map((t: any, tidx: number) => (
                          <div key={tidx} className="flex justify-between items-start gap-4 p-2 bg-[#1e293b]/10 border border-slate-850/50 rounded text-xs">
                            <div className="space-y-1">
                              <p className="font-semibold text-slate-300">{t.name}</p>
                              {!t.passed && (
                                <p className="text-[10px] text-rose-400 font-mono leading-relaxed bg-rose-950/20 p-2 rounded mt-1 border border-rose-950/50">
                                  {t.details}
                                </p>
                              )}
                            </div>
                            <span className="shrink-0 flex items-center gap-1">
                              {t.passed ? (
                                <CheckCircle className="h-4.5 w-4.5 text-emerald-500" />
                              ) : (
                                <XCircle className="h-4.5 w-4.5 text-rose-500" />
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500 text-xs border border-dashed border-slate-800 rounded">
                No regression tests executed. Click the trigger button to run postgres integration validation.
              </div>
            )}
          </div>
        )}

        {activeTab === 'reset' && (
          <div className="card bg-[#1e293b]/20 border border-slate-700/40 p-5 space-y-6">
            <div className="space-y-1.5 border-b border-slate-800 pb-4">
              <h2 className="text-sm font-bold text-slate-200">Sandbox Reset & Cleanup</h2>
              <p className="text-[10px] text-slate-400">
                Safe cleanup utility that deletes only simulator-generated records (flagged with `is_demo = true`). Production data remains unaffected.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded border border-slate-800 bg-[#1e293b]/40 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-200">Clean Conversations</p>
                  <p className="text-[10px] text-slate-400 leading-normal">Deletes messages and AI metadata parameters.</p>
                </div>
                <input
                  type="checkbox"
                  checked={resetOptions.clear_conversations}
                  onChange={(e) => setResetOptions({ ...resetOptions, clear_conversations: e.target.checked })}
                  className="toggle-checkbox shrink-0"
                />
              </div>

              <div className="p-4 rounded border border-slate-800 bg-[#1e293b]/40 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-200">Clean Customers</p>
                  <p className="text-[10px] text-slate-400 leading-normal">Deletes buyer facts, summaries, and memory events.</p>
                </div>
                <input
                  type="checkbox"
                  checked={resetOptions.clear_buyers}
                  onChange={(e) => setResetOptions({ ...resetOptions, clear_buyers: e.target.checked })}
                  className="toggle-checkbox shrink-0"
                />
              </div>

              <div className="p-4 rounded border border-slate-800 bg-[#1e293b]/40 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-200">Clean Background Tasks</p>
                  <p className="text-[10px] text-slate-400 leading-normal">Deletes queued follow-ups and execution histories.</p>
                </div>
                <input
                  type="checkbox"
                  checked={resetOptions.clear_queue}
                  onChange={(e) => setResetOptions({ ...resetOptions, clear_queue: e.target.checked })}
                  className="toggle-checkbox shrink-0"
                />
              </div>

              <div className="p-4 rounded border border-slate-800 bg-[#1e293b]/40 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-200">Clean Audit Logs</p>
                  <p className="text-[10px] text-slate-400 leading-normal">Deletes simulated action histories.</p>
                </div>
                <input
                  type="checkbox"
                  checked={resetOptions.clear_audit_logs}
                  onChange={(e) => setResetOptions({ ...resetOptions, clear_audit_logs: e.target.checked })}
                  className="toggle-checkbox shrink-0"
                />
              </div>
            </div>

            <div className="border-t border-slate-800 pt-6 flex justify-end gap-3">
              <button
                disabled={loading}
                onClick={() => setResetOptions({
                  clear_conversations: true,
                  clear_buyers: true,
                  clear_activity: true,
                  clear_queue: true,
                  clear_audit_logs: true,
                  reset_everything: true,
                })}
                className="btn-secondary py-2 px-4 cursor-pointer text-xs"
              >
                Select All
              </button>
              <button
                disabled={loading}
                onClick={handleResetData}
                className="py-2 px-4 rounded bg-rose-600 hover:bg-rose-500 text-white font-semibold transition-all border border-rose-500/20 shadow-md shadow-rose-600/10 flex items-center gap-1.5 cursor-pointer text-xs"
              >
                <Trash2 className="h-4 w-4" />
                Perform Reset
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

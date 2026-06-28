import React from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { BarChart3, TrendingUp, DollarSign, Coins, Timer, Sparkles } from 'lucide-react'
import type { AnalyticsData } from '../../types'

interface AnalyticsChartsProps {
  data: AnalyticsData | undefined
  loading: boolean
}

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ data, loading }) => {
  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#3b82f6', '#a855f7']

  if (loading) {
    return <div className="card h-128 skeleton"></div>
  }

  return (
    <div className="space-y-6">
      
      {/* Cost Analytics Panel */}
      {data?.cost_metrics && (
        <div className="card grid grid-cols-1 md:grid-cols-4 gap-4 bg-gradient-to-br from-[#1e293b] to-[#0f172a] border border-indigo-500/10">
          <div className="p-4 border-r border-slate-700/50 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400">
              <DollarSign className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total Model Cost</span>
              <p className="text-lg font-bold text-slate-100 font-mono mt-0.5">${Number(data.cost_metrics.total_cost_usd).toFixed(4)}</p>
            </div>
          </div>
          <div className="p-4 border-r border-slate-700/50 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Coins className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Avg Cost / Chat</span>
              <p className="text-lg font-bold text-slate-100 font-mono mt-0.5">${Number(data.cost_metrics.avg_cost_per_conversation).toFixed(4)}</p>
            </div>
          </div>
          <div className="p-4 border-r border-slate-700/50 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-yellow-500/10 text-yellow-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Avg Tokens / Bubble</span>
              <p className="text-lg font-bold text-slate-100 font-mono mt-0.5">{data.cost_metrics.avg_tokens_per_response}</p>
            </div>
          </div>
          <div className="p-4 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-pink-500/10 text-pink-400">
              <Timer className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Avg Cost / Qualified</span>
              <p className="text-lg font-bold text-slate-100 font-mono mt-0.5">${Number(data.cost_metrics.avg_cost_per_qualified_lead).toFixed(4)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* conversations per day */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">Conversations vs Leads Trend</span>
            <TrendingUp className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data?.conversations_per_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} />
                <YAxis stroke="#94a3b8" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Line type="monotone" dataKey="value" name="Chats" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Intent Distribution */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">Intent Distribution</span>
            <BarChart3 className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="h-64">
            {(!data?.intent_distribution || data.intent_distribution.length === 0) ? (
              <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">No intent logs inside date window.</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.intent_distribution}
                    dataKey="count"
                    nameKey="intent"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    label={({ intent, percentage }: any) => `${intent} (${percentage}%)`}
                    labelLine={false}
                  >
                    {data.intent_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Average Latency trend */}
        <div className="card space-y-4 md:col-span-2">
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider block">Average AI Response Latency (ms)</span>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.avg_response_time_per_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} />
                <YAxis stroke="#94a3b8" fontSize={10} unit="ms" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }} />
                <Bar dataKey="value" name="Latency" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  )
}

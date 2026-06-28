import React from 'react'
import {
  MessageSquare,
  Users,
  UserCheck,
  TrendingUp,
  Clock,
  CheckCircle,
  Activity,
  DollarSign,
  UserPlus,
} from 'lucide-react'
import type { OverviewMetrics } from '../../types'

interface MetricCardsProps {
  metrics: OverviewMetrics | undefined
  loading: boolean
}

export const MetricCards: React.FC<MetricCardsProps> = ({ metrics, loading }) => {
  const cards = [
    {
      label: 'Active Conversations',
      value: metrics?.active_conversations?.value,
      icon: MessageSquare,
      color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/10',
      description: 'Active in the last 24 hours',
    },
    {
      label: 'Total Customers',
      value: metrics?.total_customers?.value,
      icon: Users,
      color: 'text-slate-400 bg-slate-500/10 border-slate-500/10',
      description: 'Registered profiles',
    },
    {
      label: 'New Leads Today',
      value: metrics?.new_leads_today?.value,
      icon: UserPlus,
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/10',
      description: 'Registered since midnight',
    },
    {
      label: 'Qualified Leads',
      value: metrics?.qualified_leads?.value,
      icon: UserCheck,
      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/10',
      description: 'Stage higher than Research',
    },
    {
      label: 'Purchase Ready Leads',
      value: metrics?.purchase_ready?.value,
      icon: TrendingUp,
      color: 'text-rose-400 bg-rose-500/10 border-rose-500/10',
      description: 'In Negotiation or Ready to buy',
    },
    {
      label: 'Avg Response Time',
      value: metrics?.avg_response_time_ms?.value,
      unit: 'ms',
      icon: Clock,
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/10',
      description: 'AI model generation latency',
    },
    {
      label: 'AI Success Rate',
      value: metrics?.ai_success_rate?.value,
      unit: '%',
      icon: CheckCircle,
      color: 'text-teal-400 bg-teal-500/10 border-teal-500/10',
      description: 'Response stop triggers',
    },
    {
      label: 'Memory Updates Today',
      value: metrics?.memory_updates_today?.value,
      icon: Activity,
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/10',
      description: 'Rolling summary updates',
    },
    {
      label: 'AI Cost Today',
      value: metrics?.total_cost_today_usd?.value,
      unit: ' USD',
      icon: DollarSign,
      color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/10',
      description: 'Est. OpenAI API usage cost',
    },
  ]

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="card h-28 flex flex-col justify-between">
            <div className="flex justify-between items-center">
              <div className="h-4 w-32 skeleton"></div>
              <div className="h-8 w-8 rounded-lg skeleton"></div>
            </div>
            <div className="h-8 w-20 skeleton mt-2"></div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div
            key={card.label}
            className="card hover:border-slate-500 hover:shadow-lg transition-all duration-300 group flex items-start justify-between relative overflow-hidden"
          >
            {/* Background subtle light effects */}
            <div className="absolute top-0 right-0 w-24 h-24 bg-slate-500/5 rounded-full blur-2xl group-hover:bg-indigo-500/5 transition-all"></div>

            <div className="flex flex-col justify-between h-full min-h-[64px]">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  {card.label}
                </span>
                <span className="text-2xl font-bold text-slate-200 mt-1 block font-mono count-up">
                  {card.value !== undefined
                    ? card.unit === ' USD'
                      ? `$${card.value}`
                      : `${card.value}${card.unit || ''}`
                    : '—'}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-2">{card.description}</p>
            </div>

            <div
              className={`p-2.5 rounded-xl border flex items-center justify-center shrink-0 ${card.color}`}
            >
              <Icon className="h-5 w-5" />
            </div>
          </div>
        )
      })}
    </div>
  )
}

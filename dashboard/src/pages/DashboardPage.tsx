import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchOverview,
  fetchConversations,
  fetchConversationDetail,
  fetchCustomers,
  fetchCustomerProfile,
  fetchLeads,
  updateLeadStage,
  fetchAnalytics,
  fetchSystemHealth,
  fetchActivity,
  fetchQueue,
  fetchAuditLog,
} from '../api/dashboard'
import { useWebSocket } from '../hooks/useWebSocket'
import { Sidebar } from '../components/layout/Sidebar'
import { TopNav } from '../components/layout/TopNav'
import { MetricCards } from '../components/overview/MetricCards'
import { ConversationFeed } from '../components/conversations/ConversationFeed'
import { ConversationViewer } from '../components/conversations/ConversationViewer'
import { CustomerProfile } from '../components/customers/CustomerProfile'
import { LeadPipeline } from '../components/leads/LeadPipeline'
import { SchedulePage } from './SchedulePage'
import FollowUpPage from './FollowUpPage'
import { AnalyticsCharts } from '../components/analytics/AnalyticsCharts'
import { ActivityTimeline } from '../components/activity/ActivityTimeline'
import { QueueMonitor } from '../components/system/QueueMonitor'
import { SystemHealth } from '../components/system/SystemHealth'
import { AuditLogViewer } from '../components/audit/AuditLogViewer'
import { Shield, Users, RefreshCw, Calendar } from 'lucide-react'
import type { NavSection } from '../types'

const DeveloperToolsSection = process.env.ENABLE_DEVELOPER_TOOLS === 'true'
  ? React.lazy(() => import('./DeveloperToolsPage').then(m => ({ default: m.DeveloperToolsPage })))
  : () => null

export const DashboardPage = () => {
  const queryClient = useQueryClient()
  const [section, setSection] = useState<NavSection>('overview')
  const { connected } = useWebSocket()

  // Selection states for Chat Feed and Customer Details
  const [selectedConvoId, setSelectedConvoId] = useState<string | null>(null)
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null)

  // Search/Filter states for Chat Feed
  const [chatSearch, setChatSearch] = useState('')
  const [chatStageFilter, setChatStageFilter] = useState('')
  const [chatPage, setChatPage] = useState(1)

  // Search/Filter states for Customers
  const [custSearch, setCustSearch] = useState('')
  const [custStageFilter, setCustStageFilter] = useState('')
  const [custStatusFilter, setCustStatusFilter] = useState('')
  const [custPage, setCustPage] = useState(1)

  // ── Queries ────────────────────────────────────────────────────────────────
  const { data: overview, isLoading: loadingOverview, refetch: refetchOverview } = useQuery({
    queryKey: ['overview'],
    queryFn: fetchOverview,
  })

  const { data: conversations, isLoading: loadingConversations } = useQuery({
    queryKey: ['conversations', chatSearch, chatStageFilter, chatPage],
    queryFn: () =>
      fetchConversations({
        search: chatSearch,
        buying_stage: chatStageFilter,
        page: chatPage,
        page_size: 20,
      }),
  })

  const { data: convoDetail, isLoading: loadingConvoDetail } = useQuery({
    queryKey: ['conversationDetail', selectedConvoId],
    queryFn: () => fetchConversationDetail(selectedConvoId!),
    enabled: !!selectedConvoId,
  })

  const { data: customers, isLoading: loadingCustomers } = useQuery({
    queryKey: ['customers', custSearch, custStageFilter, custStatusFilter, custPage],
    queryFn: () =>
      fetchCustomers({
        search: custSearch,
        buying_stage: custStageFilter,
        status: custStatusFilter,
        page: custPage,
        page_size: 20,
      }),
  })

  const { data: custProfile, isLoading: loadingCustProfile, refetch: refetchCustProfile } = useQuery({
    queryKey: ['customerProfile', selectedCustomerId],
    queryFn: () => fetchCustomerProfile(selectedCustomerId!),
    enabled: !!selectedCustomerId,
  })

  const { data: leads, isLoading: loadingLeads, refetch: refetchLeads } = useQuery({
    queryKey: ['leads'],
    queryFn: fetchLeads,
  })

  const { data: analytics, isLoading: loadingAnalytics, refetch: refetchAnalytics } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => fetchAnalytics(),
  })

  const { data: health, isLoading: loadingHealth, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: fetchSystemHealth,
  })

  const { data: activity, isLoading: loadingActivity, refetch: refetchActivity } = useQuery({
    queryKey: ['activity'],
    queryFn: () => fetchActivity(50),
  })

  const { data: queue, isLoading: loadingQueue, refetch: refetchQueue } = useQuery({
    queryKey: ['queue'],
    queryFn: fetchQueue,
  })

  const { data: auditLogs, isLoading: loadingAudit, refetch: refetchAudit } = useQuery({
    queryKey: ['auditLogs'],
    queryFn: () => fetchAuditLog(100),
  })

  // ── Mutations ──────────────────────────────────────────────────────────────
  const moveLeadMutation = useMutation({
    mutationFn: ({ id, stage, reason }: { id: string; stage: string; reason?: string }) =>
      updateLeadStage(id, stage, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      queryClient.invalidateQueries({ queryKey: ['auditLogs'] })
    },
  })

  const handleMoveLead = (customerId: string, newStage: string, reason?: string) => {
    moveLeadMutation.mutate({ id: customerId, stage: newStage, reason })
  }

  // ── Refresh Handler ────────────────────────────────────────────────────────
  const handleManualRefresh = () => {
    if (section === 'overview') refetchOverview()
    else if (section === 'leads') refetchLeads()
    else if (section === 'analytics') refetchAnalytics()
    else if (section === 'activity') refetchActivity()
    else if (section === 'queue') refetchQueue()
    else if (section === 'system') refetchHealth()
    else if (section === 'audit') refetchAudit()
    else if (section === 'customers' && selectedCustomerId) refetchCustProfile()
  }

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-100 overflow-hidden font-sans">
      
      {/* 1. Sidebar Left */}
      <Sidebar currentSection={section} onSelectSection={setSection} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* 2. Top Nav */}
        <TopNav
          wsConnected={connected}
          onSelectCustomer={setSelectedCustomerId}
          onSelectConversation={setSelectedConvoId}
          onNavigate={setSection}
        />

        {/* 3. Panel Content Swapper */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Header Action bar */}
          <div className="flex justify-between items-center shrink-0">
            <div>
              <h1 className="text-xl font-bold capitalize text-slate-100">{section.replace('_', ' ')}</h1>
              <p className="text-xs text-slate-400 mt-1">
                {section === 'overview' && 'Live business performance & operational diagnostics'}
                {section === 'conversations' && 'Continuous chat timelines, metadata metrics, and playback debugging'}
                {section === 'customers' && 'Customer facts database, notes, and rolling memories'}
                {section === 'leads' && 'Visual Kanban CRM progression management'}
                {section === 'analytics' && 'Token aggregations, cost parameters, and execution speeds'}
                {section === 'activity' && 'Real-time sequential AI pipeline trace log'}
                {section === 'queue' && 'Pending background triggers and task schedulers'}
                {section === 'audit' && 'Immutable action log for compliance verification'}
                {section === 'system' && 'API link states, database status, and operational warnings'}
                {section === 'schedule' && 'Calendar management and upcoming engagement tracking'}
                {section === 'followup' && 'Pending follow-up tasks and customer outreach'}
              </p>
            </div>
            
            {/* Quick Refresh buttons */}
            {['overview', 'leads', 'analytics', 'activity', 'queue', 'system', 'audit'].includes(section) && (
              <button
                onClick={handleManualRefresh}
                className="btn-ghost flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Refresh Data
              </button>
            )}
          </div>

          {/* Nav Views */}
          <div className="fade-in h-full">
            {section === 'overview' && (
              <div className="space-y-6">
                <MetricCards metrics={overview} loading={loadingOverview} />
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    <SystemHealth health={health} loading={loadingHealth} onRefresh={refetchHealth} />
                  </div>
                  <div>
                    <QueueMonitor queue={queue} loading={loadingQueue} onRefresh={refetchQueue} />
                  </div>
                </div>
              </div>
            )}

            {section === 'conversations' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 border border-[#334155] rounded-xl overflow-hidden bg-[#1e293b]/20 h-[calc(100vh-180px)]">
                <div className="lg:col-span-1 border-r border-[#334155] h-full overflow-hidden">
                  <ConversationFeed
                    pageData={conversations}
                    loading={loadingConversations}
                    selectedId={selectedConvoId}
                    onSelect={setSelectedConvoId}
                    page={chatPage}
                    onPageChange={setChatPage}
                    search={chatSearch}
                    onSearchChange={setChatSearch}
                    stageFilter={chatStageFilter}
                    onStageFilterChange={setChatStageFilter}
                  />
                </div>
                <div className="lg:col-span-2 h-full overflow-hidden">
                  <ConversationViewer convo={convoDetail} loading={loadingConvoDetail} />
                </div>
              </div>
            )}

            {section === 'customers' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 border border-[#334155] rounded-xl overflow-hidden bg-[#1e293b]/20 h-[calc(100vh-180px)]">
                {/* Left customer list */}
                <div className="lg:col-span-1 border-r border-[#334155] h-full flex flex-col overflow-hidden bg-[#1e293b]/20">
                  <div className="p-4 border-b border-[#334155] space-y-3">
                    <input
                      type="text"
                      className="input"
                      placeholder="Search customer records..."
                      value={custSearch}
                      onChange={(e) => setCustSearch(e.target.value)}
                    />
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-2">
                    {loadingCustomers ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="h-16 card skeleton"></div>
                      ))
                    ) : !customers?.items || customers.items.length === 0 ? (
                      <div className="text-center py-12 text-slate-500 text-xs">No customer records.</div>
                    ) : (
                      customers.items.map((cust) => (
                        <button
                          key={cust.id}
                          onClick={() => setSelectedCustomerId(cust.id)}
                          className={`w-full text-left p-3.5 rounded-lg border transition-all cursor-pointer ${
                            selectedCustomerId === cust.id
                              ? 'bg-indigo-500/10 border-indigo-500/40 text-slate-100'
                              : 'bg-[#1e293b]/40 border-slate-700/50 hover:bg-[#1e293b]/80'
                          }`}
                        >
                          <p className="text-xs font-bold text-slate-200">{cust.name || 'Unnamed'}</p>
                          <span className="text-[10px] text-slate-500 font-mono block mt-0.5">{cust.phone}</span>
                        </button>
                      ))
                    )}
                  </div>
                </div>

                {/* Right profile panel details */}
                <div className="lg:col-span-2 h-full overflow-hidden">
                  <CustomerProfile
                    profile={custProfile}
                    loading={loadingCustProfile}
                    onRefresh={refetchCustProfile}
                  />
                </div>
              </div>
            )}

            {section === 'leads' && (
              <LeadPipeline
                pipeline={leads}
                loading={loadingLeads}
                onMoveLead={handleMoveLead}
              />
            )}
            
            {section === 'schedule' && (
              <SchedulePage />
            )}

            {section === 'followup' && (
              <FollowUpPage />
            )}

            {section === 'analytics' && (
              <AnalyticsCharts data={analytics} loading={loadingAnalytics} />
            )}

            {section === 'activity' && (
              <ActivityTimeline events={activity} loading={loadingActivity} onRefresh={refetchActivity} />
            )}

            {section === 'queue' && (
              <QueueMonitor queue={queue} loading={loadingQueue} onRefresh={refetchQueue} />
            )}

            {section === 'system' && (
              <SystemHealth health={health} loading={loadingHealth} onRefresh={refetchHealth} />
            )}

            {section === 'audit' && (
              <AuditLogViewer logs={auditLogs} loading={loadingAudit} onRefresh={refetchAudit} />
            )}

            {section === 'developer_tools' && (
              <React.Suspense fallback={<div className="h-64 card skeleton"></div>}>
                <DeveloperToolsSection />
              </React.Suspense>
            )}
          </div>

        </main>
      </div>
    </div>
  )
}

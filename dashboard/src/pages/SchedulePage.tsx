import React, { useState, useEffect, useCallback } from 'react'
import {
  fetchTodaySchedule, fetchUpcomingSchedule, fetchScheduleOverview,
  fetchCandidates, fetchEvents, completeEvent, cancelEvent,
  confirmEvent, promoteCandidate, abandonCandidate
} from '../api/scheduling'
import EventCard from '../components/schedule/EventCard'
import CandidateCard from '../components/schedule/CandidateCard'
import { CreateEventModal } from '../components/schedule/CreateEventModal'
import type { ScheduledEventSummary, SchedulingCandidate, ScheduleOverview } from '../types'
import { Calendar, Inbox, Clock, RefreshCw } from 'lucide-react'

export const SchedulePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'today' | 'upcoming' | 'candidates' | 'callbacks' | 'followups'>('today')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  
  const [overview, setOverview] = useState<ScheduleOverview | null>(null)
  const [todayEvents, setTodayEvents] = useState<ScheduledEventSummary[]>([])
  const [upcomingEvents, setUpcomingEvents] = useState<ScheduledEventSummary[]>([])
  const [candidates, setCandidates] = useState<SchedulingCandidate[]>([])
  const [callbacks, setCallbacks] = useState<ScheduledEventSummary[]>([])
  const [followups, setFollowups] = useState<ScheduledEventSummary[]>([])
  
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const ov = await fetchScheduleOverview()
      setOverview(ov)
      
      if (activeTab === 'today') setTodayEvents(await fetchTodaySchedule())
      if (activeTab === 'upcoming') setUpcomingEvents(await fetchUpcomingSchedule(7))
      if (activeTab === 'candidates') setCandidates(await fetchCandidates())
      if (activeTab === 'callbacks') {
        const res = await fetchEvents({ event_type: 'callback', status: 'pending' })
        setCallbacks(res.items)
      }
      if (activeTab === 'followups') {
        const res = await fetchEvents({ event_type: 'followup', status: 'pending' })
        setFollowups(res.items)
      }
    } catch (e) {
      console.error("Failed to load schedule data", e)
    } finally {
      setLoading(false)
    }
  }, [activeTab])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleAction = async (action: Promise<any>) => {
    await action
    loadData()
  }

  const renderContent = () => {
    if (loading) {
      return (
        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ height: 100, background: 'rgba(255,255,255,0.02)', borderRadius: 12, animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      )
    }

    if (activeTab === 'today') {
      if (!todayEvents.length) return <EmptyState icon={<Calendar size={48}/>} title="No events scheduled for today" />
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
          {todayEvents.map(ev => (
            <EventCard 
              key={ev.id} event={ev} 
              onConfirm={() => handleAction(confirmEvent(ev.id))}
              onComplete={() => handleAction(completeEvent(ev.id))}
              onCancel={() => handleAction(cancelEvent(ev.id, "Cancelled from dashboard"))}
            />
          ))}
        </div>
      )
    }

    if (activeTab === 'upcoming') {
      if (!upcomingEvents.length) return <EmptyState icon={<Calendar size={48}/>} title="No upcoming events in the next 7 days" />
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
          {upcomingEvents.map(ev => (
             <EventCard 
             key={ev.id} event={ev} 
             onConfirm={() => handleAction(confirmEvent(ev.id))}
             onComplete={() => handleAction(completeEvent(ev.id))}
             onCancel={() => handleAction(cancelEvent(ev.id, "Cancelled from dashboard"))}
           />
          ))}
        </div>
      )
    }

    if (activeTab === 'candidates') {
      const pendingCandidates = candidates.filter(c => c.status === 'pending_info' || c.status === 'ready')
      if (!pendingCandidates.length) return <EmptyState icon={<Inbox size={48}/>} title="No pending scheduling proposals" />
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
          <div style={{ color: '#94a3b8', fontSize: 13, marginBottom: 8 }}>
            AI-proposed events awaiting information from the customer
          </div>
          {pendingCandidates.map(c => (
            <CandidateCard
              key={c.id} candidate={c}
              onPromote={() => handleAction(promoteCandidate(c.id))}
              onAbandon={() => handleAction(abandonCandidate(c.id))}
            />
          ))}
        </div>
      )
    }

    if (activeTab === 'callbacks') {
      if (!callbacks.length) return <EmptyState icon={<Clock size={48}/>} title="No pending callbacks" />
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
          {callbacks.map(ev => (
             <EventCard 
             key={ev.id} event={ev} 
             onConfirm={() => handleAction(confirmEvent(ev.id))}
             onComplete={() => handleAction(completeEvent(ev.id))}
             onCancel={() => handleAction(cancelEvent(ev.id, "Cancelled from dashboard"))}
           />
          ))}
        </div>
      )
    }

    if (activeTab === 'followups') {
      if (!followups.length) return <EmptyState icon={<RefreshCw size={48}/>} title="No pending follow-ups" />
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
          {followups.map(ev => (
             <EventCard 
             key={ev.id} event={ev} 
             onConfirm={() => handleAction(confirmEvent(ev.id))}
             onComplete={() => handleAction(completeEvent(ev.id))}
             onCancel={() => handleAction(cancelEvent(ev.id, "Cancelled from dashboard"))}
           />
          ))}
        </div>
      )
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#e2e8f0', margin: 0 }}>Schedule</h1>
          <p style={{ color: '#94a3b8', margin: '4px 0 0', fontSize: 14 }}>Manage events, follow-ups, and AI proposals</p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          style={{
            background: 'linear-gradient(135deg, #6c63ff, #8b5cf6)',
            border: 'none', padding: '10px 20px', borderRadius: 8,
            color: 'white', fontWeight: 600, cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(108,99,255,0.3)',
          }}
        >
          + Create Event
        </button>
      </div>

      {/* Overview stats */}
      <div style={{ display: 'flex', gap: 12, padding: '20px 32px', background: 'rgba(0,0,0,0.1)' }}>
        <StatPill label="Pending" value={overview?.pending} color="#f59e0b" />
        <StatPill label="Confirmed" value={overview?.confirmed} color="#6c63ff" />
        <StatPill label="In Progress" value={overview?.in_progress} color="#3b82f6" />
        <StatPill label="Upcoming 7D" value={overview?.upcoming_7_days} color="#8b5cf6" />
        <StatPill label="Pending Callbacks" value={overview?.pending_callbacks} color="#f97316" />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', padding: '0 32px', borderBottom: '1px solid rgba(255,255,255,0.05)', gap: 32 }}>
        {(['today', 'upcoming', 'candidates', 'callbacks', 'followups'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              background: 'none', border: 'none',
              padding: '16px 0', cursor: 'pointer',
              color: activeTab === tab ? '#6c63ff' : '#94a3b8',
              fontWeight: activeTab === tab ? 700 : 500,
              fontSize: 14, textTransform: 'capitalize',
              borderBottom: activeTab === tab ? '2px solid #6c63ff' : '2px solid transparent',
              transition: 'all 0.2s ease'
            }}
          >
            {tab}
            {tab === 'candidates' && overview?.active_candidates ? (
              <span style={{ marginLeft: 8, background: '#ef4444', color: 'white', padding: '2px 6px', borderRadius: 10, fontSize: 11 }}>
                {overview.active_candidates}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          {renderContent()}
        </div>
      </div>

      <CreateEventModal 
        isOpen={isCreateModalOpen} 
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={() => {
          setIsCreateModalOpen(false)
          loadData()
        }}
      />
    </div>
  )
}

const StatPill = ({ label, value, color }: { label: string, value?: number, color: string }) => (
  <div style={{ 
    display: 'flex', alignItems: 'center', gap: 12, 
    background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)',
    padding: '8px 16px', borderRadius: 100, flex: 1
  }}>
    <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
    <div style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>{label}</div>
    <div style={{ color: '#e2e8f0', fontSize: 16, fontWeight: 700, marginLeft: 'auto' }}>{value ?? '-'}</div>
  </div>
)

const EmptyState = ({ icon, title }: { icon: React.ReactNode, title: string }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 0', color: '#64748b' }}>
    <div style={{ marginBottom: 16, opacity: 0.5 }}>{icon}</div>
    <div style={{ fontSize: 16, fontWeight: 500 }}>{title}</div>
  </div>
)

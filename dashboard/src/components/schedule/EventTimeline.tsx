import React, { useEffect, useState } from 'react'
import { fetchCustomerEvents } from '../../api/scheduling'
import type { ScheduledEventSummary } from '../../types'

export const EventTimeline: React.FC<{ customerId: string, className?: string }> = ({ customerId, className }) => {
  const [events, setEvents] = useState<ScheduledEventSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCustomerEvents(customerId)
      .then(data => setEvents(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [customerId])

  if (loading) {
    return <div style={{ color: '#94a3b8', fontSize: 13 }}>Loading timeline...</div>
  }

  if (error) {
    return <div style={{ color: '#ef4444', fontSize: 13 }}>Failed to load timeline.</div>
  }

  if (events.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0', color: '#64748b' }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>📅</div>
        <div style={{ fontSize: 14 }}>No events scheduled</div>
      </div>
    )
  }

  return (
    <div className={className} style={{ position: 'relative', paddingLeft: 16 }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute', top: 8, bottom: 8, left: 23,
        width: 2, background: 'rgba(255,255,255,0.1)'
      }} />

      {events.map((ev, i) => {
        const isCompleted = ev.status === 'completed'
        const isCancelled = ev.status === 'cancelled'
        const isPending = ev.status === 'pending' || ev.status === 'confirmed'
        
        let color = '#3b82f6'
        if (isCompleted) color = '#10b981'
        if (isCancelled) color = '#6b7280'
        if (isPending) color = '#6c63ff'

        return (
          <div key={ev.id} style={{ display: 'flex', gap: 16, marginBottom: i === events.length - 1 ? 0 : 24, position: 'relative' }}>
            {/* Dot */}
            <div style={{
              width: 16, height: 16, borderRadius: '50%',
              background: isPending ? 'transparent' : color,
              border: `2px solid ${color}`,
              marginTop: 4, position: 'relative', zIndex: 2,
              boxShadow: `0 0 0 4px #1e293b`
            }} />

            {/* Content */}
            <div style={{ flex: 1, background: 'rgba(255,255,255,0.03)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ 
                  fontWeight: 600, fontSize: 14, color: isCancelled ? '#64748b' : '#e2e8f0',
                  textDecoration: isCancelled ? 'line-through' : 'none'
                }}>
                  {ev.title}
                </span>
                <span style={{ fontSize: 11, color: color, background: `${color}20`, padding: '2px 6px', borderRadius: 4, fontWeight: 600 }}>
                  {ev.status.toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                {ev.scheduled_for ? new Date(ev.scheduled_for).toLocaleString() : 'Time TBD'}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

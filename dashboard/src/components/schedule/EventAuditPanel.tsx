import React, { useEffect, useState } from 'react'
import { fetchEventAuditLog } from '../../api/scheduling'
import type { EventAuditEntry } from '../../types'

export const EventAuditPanel: React.FC<{ eventId: string }> = ({ eventId }) => {
  const [entries, setEntries] = useState<EventAuditEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEventAuditLog(eventId).then(setEntries).finally(() => setLoading(false))
  }, [eventId])

  if (loading) return <div style={{ color: '#94a3b8', fontSize: 13 }}>Loading audit log...</div>
  
  if (entries.length === 0) return <div style={{ color: '#64748b', fontSize: 13 }}>No audit entries found.</div>

  const getActionColor = (action: string) => {
    if (action.includes('created')) return '#3b82f6'
    if (action.includes('confirmed')) return '#6c63ff'
    if (action.includes('completed')) return '#10b981'
    if (action.includes('cancelled')) return '#ef4444'
    if (action.includes('assigned')) return '#f59e0b'
    return '#94a3b8'
  }

  const getActorIcon = (type: string) => {
    if (type === 'ai') return '🤖'
    if (type === 'user') return '👤'
    return '⚙️'
  }

  return (
    <div style={{ position: 'relative', paddingLeft: 12 }}>
      <div style={{ position: 'absolute', top: 8, bottom: 8, left: 19, width: 2, background: 'rgba(255,255,255,0.08)' }} />
      {entries.map((entry, i) => {
        const color = getActionColor(entry.action)
        return (
          <div key={entry.id} style={{ display: 'flex', gap: 12, marginBottom: i === entries.length - 1 ? 0 : 20, position: 'relative' }}>
            <div style={{
              width: 16, height: 16, borderRadius: '50%', background: '#1e293b',
              border: `2px solid ${color}`, marginTop: 4, zIndex: 2
            }} />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                <span style={{ fontSize: 13 }}>{getActorIcon(entry.actor_type)}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>{entry.action}</span>
              </div>
              <div style={{ fontSize: 11, color: '#64748b' }}>
                {new Date(entry.created_at).toLocaleString()}
                {entry.from_status && entry.to_status && (
                  <span style={{ marginLeft: 8 }}>
                    {entry.from_status} → <span style={{ color: color }}>{entry.to_status}</span>
                  </span>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

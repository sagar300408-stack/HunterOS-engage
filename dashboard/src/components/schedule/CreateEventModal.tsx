import React, { useState } from 'react'
import { createEvent } from '../../api/scheduling'
import type { ScheduledEvent, EventType } from '../../types'

const EVENT_TYPES: { value: EventType; label: string; icon: string }[] = [
  { value: 'meeting',    label: 'Meeting',    icon: '📅' },
  { value: 'site_visit', label: 'Site Visit', icon: '🏠' },
  { value: 'callback',   label: 'Callback',   icon: '📞' },
  { value: 'followup',   label: 'Follow-up',  icon: '🔄' },
  { value: 'reminder',   label: 'Reminder',   icon: '🔔' },
  { value: 'task',       label: 'Task',       icon: '✅' },
]

const METADATA_FIELDS: Record<EventType, { key: string; label: string; placeholder: string; required?: boolean }[]> = {
  meeting:    [
    { key: 'meeting_type', label: 'Meeting Type', placeholder: 'online / in_person / phone' },
    { key: 'meeting_link', label: 'Meeting Link', placeholder: 'https://meet.google.com/...' },
    { key: 'agenda',       label: 'Agenda',       placeholder: 'Discussion topics...' },
  ],
  site_visit: [
    { key: 'location', label: 'Location', placeholder: 'Property address or area', required: true },
    { key: 'agent_name', label: 'Agent Name', placeholder: 'Assigned agent' },
  ],
  callback:   [
    { key: 'preferred_time', label: 'Preferred Time', placeholder: 'e.g. After 6 PM', required: true },
    { key: 'phone', label: 'Phone', placeholder: 'Callback number' },
  ],
  followup:   [
    { key: 'follow_up_reason', label: 'Reason', placeholder: 'Why this follow-up?' },
  ],
  reminder:   [
    { key: 'reminder_message', label: 'Reminder Message', placeholder: 'Reminder text...', required: true },
    { key: 'channel', label: 'Channel', placeholder: 'whatsapp / email / sms' },
  ],
  task:       [
    { key: 'task_description', label: 'Task Description', placeholder: 'What needs to be done?', required: true },
    { key: 'department', label: 'Department', placeholder: 'sales / support / management' },
  ],
}

export interface CreateEventModalProps {
  isOpen:            boolean
  onClose:           () => void
  onCreated:         (event: ScheduledEvent) => void
  defaultCustomerId?: string
}

export const CreateEventModal: React.FC<CreateEventModalProps> = ({
  isOpen, onClose, onCreated, defaultCustomerId,
}) => {
  const [eventType,     setEventType]     = useState<EventType>('meeting')
  const [title,         setTitle]         = useState('')
  const [description,   setDescription]   = useState('')
  const [scheduledFor,  setScheduledFor]  = useState('')
  const [durationMin,   setDurationMin]   = useState<number | ''>('')
  const [priority,      setPriority]      = useState<'high' | 'medium' | 'low'>('medium')
  const [customerId,    setCustomerId]     = useState(defaultCustomerId ?? '')
  const [assignedTo,    setAssignedTo]    = useState('')
  const [metaValues,    setMetaValues]    = useState<Record<string, string>>({})
  const [loading,       setLoading]       = useState(false)
  const [error,         setError]         = useState<string | null>(null)

  if (!isOpen) return null

  const handleMetaChange = (key: string, val: string) =>
    setMetaValues(prev => ({ ...prev, [key]: val }))

  const getLocalIsoString = (datetimeLocalValue: string) => {
    if (!datetimeLocalValue) return undefined;
    const d = new Date(datetimeLocalValue);
    const tzOffset = -d.getTimezoneOffset();
    const diff = tzOffset >= 0 ? '+' : '-';
    const pad = (n: number) => `${Math.floor(Math.abs(n))}`.padStart(2, '0');
    const offset = diff + pad(tzOffset / 60) + ':' + pad(tzOffset % 60);
    
    // Format YYYY-MM-DDTHH:mm:ss
    const localIso = d.getFullYear() +
      '-' + pad(d.getMonth() + 1) +
      '-' + pad(d.getDate()) +
      'T' + pad(d.getHours()) +
      ':' + pad(d.getMinutes()) +
      ':' + pad(d.getSeconds());

    return localIso + offset;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const metadata = Object.fromEntries(
        Object.entries(metaValues).filter(([, v]) => v.trim() !== '')
      )
      const event = await createEvent({
        event_type:       eventType,
        title:            title.trim() || `${eventType.replace('_', ' ')} Event`,
        description:      description || undefined,
        scheduled_for:    getLocalIsoString(scheduledFor),
        duration_minutes: durationMin !== '' ? Number(durationMin) : undefined,
        priority,
        metadata:         Object.keys(metadata).length ? metadata : undefined,
        customer_id:      customerId || undefined,
        assigned_to:      assignedTo || undefined,
      })
      onCreated(event)
      onClose()
    } catch (err: unknown) {
      setError((err as Error).message ?? 'Failed to create event')
    } finally {
      setLoading(false)
    }
  }

  const metaFields = METADATA_FIELDS[eventType] ?? []

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(6px)',
          zIndex: 1000,
          animation: 'fadeIn 0.15s ease',
        }}
      />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '100%', maxWidth: 600,
        maxHeight: '90vh', overflowY: 'auto',
        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 16,
        boxShadow: '0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(108,99,255,0.15)',
        zIndex: 1001,
        padding: 28,
        animation: 'slideUp 0.2s ease',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#e2e8f0' }}>
              Create Event
            </h2>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
              Schedule a new business action manually
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#94a3b8', fontSize: 18, cursor: 'pointer',
              borderRadius: 8, width: 32, height: 32,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >×</button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Event type selector */}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Event Type</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {EVENT_TYPES.map(t => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => { setEventType(t.value); setMetaValues({}) }}
                  style={{
                    fontSize: 12, fontWeight: 600, cursor: 'pointer',
                    padding: '6px 12px', borderRadius: 8,
                    border: eventType === t.value
                      ? '1px solid rgba(108,99,255,0.6)'
                      : '1px solid rgba(255,255,255,0.08)',
                    background: eventType === t.value
                      ? 'rgba(108,99,255,0.2)'
                      : 'rgba(255,255,255,0.03)',
                    color: eventType === t.value ? '#a5b4fc' : '#94a3b8',
                    transition: 'all 0.15s',
                  }}
                >
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Title */}
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>Title</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder={`e.g. Site Visit — Whitefield`}
              style={inputStyle}
            />
          </div>

          {/* Description */}
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>Description <span style={{ color: '#475569' }}>(optional)</span></label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Additional context or notes..."
              rows={2}
              style={{ ...inputStyle, resize: 'vertical', minHeight: 60 }}
            />
          </div>

          {/* Scheduled for + Duration */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            <div>
              <label style={labelStyle}>Scheduled For <span style={{ color: '#475569' }}>(optional)</span></label>
              <input
                type="datetime-local"
                value={scheduledFor}
                onChange={e => setScheduledFor(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Duration (minutes)</label>
              <input
                type="number"
                value={durationMin}
                onChange={e => setDurationMin(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="60"
                min={1}
                style={inputStyle}
              />
            </div>
          </div>

          {/* Priority */}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Priority</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['high', 'medium', 'low'] as const).map(p => {
                const colors = { high: '#ef4444', medium: '#f59e0b', low: '#6b7280' }
                const col = colors[p]
                return (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPriority(p)}
                    style={{
                      flex: 1, padding: '6px 0', borderRadius: 8, cursor: 'pointer',
                      fontSize: 12, fontWeight: 600, textTransform: 'capitalize',
                      border: priority === p ? `1px solid ${col}66` : '1px solid rgba(255,255,255,0.08)',
                      background: priority === p ? `${col}20` : 'rgba(255,255,255,0.03)',
                      color: priority === p ? col : '#64748b',
                      transition: 'all 0.15s',
                    }}
                  >
                    {p}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Dynamic metadata fields */}
          {metaFields.length > 0 && (
            <div style={{
              marginBottom: 16, padding: 14,
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 10,
            }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#6c63ff', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 12 }}>
                Event Details
              </div>
              {metaFields.map(f => (
                <div key={f.key} style={{ marginBottom: 12 }}>
                  <label style={labelStyle}>
                    {f.label}
                    {f.required && <span style={{ color: '#ef4444', marginLeft: 3 }}>*</span>}
                  </label>
                  <input
                    value={metaValues[f.key] ?? ''}
                    onChange={e => handleMetaChange(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    style={inputStyle}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Customer + Assign */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
            <div>
              <label style={labelStyle}>Customer ID <span style={{ color: '#475569' }}>(optional)</span></label>
              <input
                value={customerId}
                onChange={e => setCustomerId(e.target.value)}
                placeholder="UUID"
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Assign To <span style={{ color: '#475569' }}>(User ID)</span></label>
              <input
                value={assignedTo}
                onChange={e => setAssignedTo(e.target.value)}
                placeholder="UUID"
                style={inputStyle}
              />
            </div>
          </div>

          {error && (
            <div style={{
              marginBottom: 16, padding: '10px 14px',
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.2)',
              borderRadius: 8, color: '#f87171', fontSize: 13,
            }}>
              {error}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '9px 20px', borderRadius: 8, cursor: 'pointer',
                fontSize: 13, fontWeight: 600,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#94a3b8',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '9px 24px', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 13, fontWeight: 600, color: '#fff',
                background: loading ? 'rgba(108,99,255,0.4)' : 'linear-gradient(135deg, #6c63ff, #8b5cf6)',
                border: 'none',
                boxShadow: loading ? 'none' : '0 4px 16px rgba(108,99,255,0.3)',
                transition: 'all 0.15s',
              }}
            >
              {loading ? 'Creating…' : '+ Create Event'}
            </button>
          </div>
        </form>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
        @keyframes slideUp { from { transform: translate(-50%, -48%); opacity: 0 } to { transform: translate(-50%, -50%); opacity: 1 } }
      `}</style>
    </>
  )
}

// ── Styles ─────────────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600,
  color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.3px',
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8, color: '#e2e8f0', fontSize: 13,
  outline: 'none', boxSizing: 'border-box',
  transition: 'border-color 0.15s',
  fontFamily: 'inherit',
}

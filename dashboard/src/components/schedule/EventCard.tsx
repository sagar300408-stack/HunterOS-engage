import React from 'react'
import type { ScheduledEvent, ScheduledEventSummary, EventType, EventStatus } from '../../types'

// ── Helpers ──────────────────────────────────────────────────────────────────

const EVENT_TYPE_COLOR: Record<EventType, string> = {
  meeting: '#6c63ff',
  site_visit: '#3b82f6',
  callback: '#f59e0b',
  followup: '#10b981',
  reminder: '#f97316',
  task: '#ef4444',
}

const EVENT_TYPE_ICON: Record<EventType, string> = {
  meeting: '📅',
  site_visit: '🏠',
  callback: '📞',
  followup: '🔄',
  reminder: '🔔',
  task: '✅',
}

const STATUS_COLOR: Record<EventStatus, string> = {
  pending: '#f59e0b',
  confirmed: '#6c63ff',
  in_progress: '#3b82f6',
  completed: '#10b981',
  cancelled: '#6b7280',
  rescheduled: '#8b5cf6',
}

const STATUS_LABEL: Record<EventStatus, string> = {
  pending: 'Pending',
  confirmed: 'Confirmed',
  in_progress: 'In Progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
  rescheduled: 'Rescheduled',
}

const PRIORITY_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#6b7280',
}

function formatRelative(iso?: string): string {
  if (!iso) return 'Not scheduled'
  const diff = new Date(iso).getTime() - Date.now()
  const abs = Math.abs(diff)
  const mins = Math.floor(abs / 60000)
  const hrs = Math.floor(abs / 3600000)
  const days = Math.floor(abs / 86400000)
  const past = diff < 0
  if (mins < 1) return past ? 'Just now' : 'Now'
  if (mins < 60) return past ? `${mins}m ago` : `in ${mins}m`
  if (hrs < 24) return past ? `${hrs}h ago` : `in ${hrs}h`
  return past ? `${days}d ago` : `in ${days}d`
}

function formatAbsolute(iso?: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ── Component ─────────────────────────────────────────────────────────────────

interface EventCardProps {
  event: ScheduledEventSummary | ScheduledEvent
  onConfirm?: (id: string) => void
  onComplete?: (id: string) => void
  onCancel?: (id: string) => void
  onAssign?: (id: string) => void
  onClick?: (id: string) => void
  compact?: boolean
}

const EventCard: React.FC<EventCardProps> = ({
  event,
  onConfirm,
  onComplete,
  onCancel,
  onAssign,
  onClick,
  compact = false,
}) => {
  const typeColor = EVENT_TYPE_COLOR[event.event_type] ?? '#6c63ff'
  const typeIcon = EVENT_TYPE_ICON[event.event_type] ?? '📌'
  const statusColor = STATUS_COLOR[event.status] ?? '#6b7280'
  const priorityColor = PRIORITY_COLOR[event.priority] ?? '#6b7280'

  // Determine allowed transitions from extended type
  const allowedTransitions: string[] =
    (event as ScheduledEvent).allowed_transitions ?? []

  const canConfirm =
    onConfirm &&
    (event.status === 'pending' ||
      allowedTransitions.includes('confirm'))
  const canComplete =
    onComplete &&
    (event.status === 'confirmed' ||
      event.status === 'in_progress' ||
      allowedTransitions.includes('complete'))
  const canCancel =
    onCancel &&
    event.status !== 'completed' &&
    event.status !== 'cancelled' &&
    (allowedTransitions.length === 0 || allowedTransitions.includes('cancel'))

  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={() => onClick?.(event.id)}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.(event.id)}
      style={{
        background: 'rgba(30,41,59,0.6)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderLeft: `3px solid ${typeColor}`,
        borderRadius: 12,
        padding: compact ? '0.75rem 1rem' : '1rem 1.125rem',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
      className="event-card"
    >
      {/* Subtle glow top-right */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 80,
          height: 80,
          background: `radial-gradient(circle at top right, ${typeColor}18, transparent 70%)`,
          pointerEvents: 'none',
        }}
      />

      {/* ── Header row ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        {/* Event type icon */}
        <span style={{ fontSize: compact ? 18 : 22, lineHeight: 1, flexShrink: 0 }}>
          {typeIcon}
        </span>

        {/* Title + badges */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: compact ? '0.8125rem' : '0.9375rem',
                fontWeight: 600,
                color: '#e2e8f0',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {event.title}
            </span>

            {/* AI badge */}
            {event.created_by_ai && (
              <span
                title="Created by AI"
                style={{
                  fontSize: '0.6875rem',
                  background: 'rgba(108,99,255,0.15)',
                  border: '1px solid rgba(108,99,255,0.3)',
                  borderRadius: 999,
                  padding: '1px 7px',
                  color: '#a5b4fc',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 3,
                  flexShrink: 0,
                }}
              >
                🤖 AI
              </span>
            )}

            {/* Priority badge */}
            <span
              style={{
                fontSize: '0.6875rem',
                background: `${priorityColor}18`,
                border: `1px solid ${priorityColor}40`,
                borderRadius: 999,
                padding: '1px 7px',
                color: priorityColor,
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              {event.priority}
            </span>
          </div>

          {/* Event type label */}
          <span
            style={{
              fontSize: '0.7rem',
              color: typeColor,
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {event.event_type.replace('_', ' ')}
          </span>
        </div>

        {/* Status badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            flexShrink: 0,
            background: `${statusColor}12`,
            border: `1px solid ${statusColor}30`,
            borderRadius: 999,
            padding: '2px 9px',
          }}
        >
          {/* Pulse dot */}
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: statusColor,
              display: 'inline-block',
              flexShrink: 0,
            }}
            className={event.status === 'pending' ? 'pulse-amber' : undefined}
          />
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: statusColor }}>
            {STATUS_LABEL[event.status]}
          </span>
        </div>
      </div>

      {/* ── Time row ── */}
      {!compact && event.scheduled_for && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 10,
            fontSize: '0.8125rem',
            color: '#94a3b8',
          }}
        >
          <span>🕐</span>
          <span style={{ color: '#e2e8f0', fontWeight: 500 }}>
            {formatRelative(event.scheduled_for)}
          </span>
          <span style={{ color: '#475569' }}>·</span>
          <span>{formatAbsolute(event.scheduled_for)}</span>
          {(event as ScheduledEvent).duration_minutes && (
            <>
              <span style={{ color: '#475569' }}>·</span>
              <span>{(event as ScheduledEvent).duration_minutes}m</span>
            </>
          )}
        </div>
      )}

      {/* ── Meta row (customer, assignee) ── */}
      {!compact && (event.customer_id || event.assigned_to) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            marginTop: 8,
            flexWrap: 'wrap',
          }}
        >
          {event.customer_id && (
            <span
              style={{
                fontSize: '0.7rem',
                background: 'rgba(99,102,241,0.1)',
                border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: 999,
                padding: '2px 9px',
                color: '#a5b4fc',
                fontFamily: 'monospace',
              }}
            >
              👤 {event.customer_id.slice(0, 8)}…
            </span>
          )}
          {event.assigned_to && (
            <span
              style={{
                fontSize: '0.7rem',
                background: 'rgba(16,185,129,0.08)',
                border: '1px solid rgba(16,185,129,0.2)',
                borderRadius: 999,
                padding: '2px 9px',
                color: '#6ee7b7',
                fontFamily: 'monospace',
              }}
            >
              🎯 {event.assigned_to.slice(0, 8)}…
            </span>
          )}
        </div>
      )}

      {/* ── Actions row ── */}
      {(canConfirm || canComplete || canCancel || onAssign) && (
        <div
          style={{
            display: 'flex',
            gap: 6,
            marginTop: 12,
            borderTop: '1px solid rgba(255,255,255,0.06)',
            paddingTop: 10,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {canConfirm && (
            <button
              onClick={() => onConfirm!(event.id)}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '4px 12px',
                borderRadius: 6,
                border: '1px solid rgba(108,99,255,0.4)',
                background: 'rgba(108,99,255,0.12)',
                color: '#a5b4fc',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              ✓ Confirm
            </button>
          )}
          {canComplete && (
            <button
              onClick={() => onComplete!(event.id)}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '4px 12px',
                borderRadius: 6,
                border: '1px solid rgba(16,185,129,0.4)',
                background: 'rgba(16,185,129,0.12)',
                color: '#6ee7b7',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              ✓ Complete
            </button>
          )}
          {onAssign && (
            <button
              onClick={() => onAssign!(event.id)}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '4px 12px',
                borderRadius: 6,
                border: '1px solid rgba(245,158,11,0.3)',
                background: 'rgba(245,158,11,0.08)',
                color: '#fcd34d',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              Assign
            </button>
          )}
          {canCancel && (
            <button
              onClick={() => onCancel!(event.id)}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '4px 12px',
                borderRadius: 6,
                border: '1px solid rgba(239,68,68,0.3)',
                background: 'rgba(239,68,68,0.07)',
                color: '#fca5a5',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              ✕ Cancel
            </button>
          )}
        </div>
      )}

      <style>{`
        .event-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 32px rgba(108, 99, 255, 0.15);
        }
      `}</style>
    </div>
  )
}

export default EventCard

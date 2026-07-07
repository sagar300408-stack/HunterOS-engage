import React from 'react'
import type { SchedulingCandidate, EventType } from '../../types'

const EVENT_TYPE_ICON: Record<EventType, string> = {
  meeting: '📅',
  site_visit: '🏠',
  callback: '📞',
  followup: '🔄',
  reminder: '🔔',
  task: '✅',
}

const STATUS_LABEL: Record<SchedulingCandidate['status'], string> = {
  pending_info: 'Awaiting Info',
  ready: 'Ready to Promote',
  promoted: 'Promoted',
  abandoned: 'Abandoned',
}

interface CandidateCardProps {
  candidate: SchedulingCandidate
  onPromote?: (id: string) => void
  onAbandon?: (id: string) => void
}

const CandidateCard: React.FC<CandidateCardProps> = ({ candidate, onPromote, onAbandon }) => {
  const icon = EVENT_TYPE_ICON[candidate.suggested_event_type] ?? '📌'
  const isReady = candidate.status === 'ready'
  const isPending = candidate.status === 'pending_info'

  const collectedKeys = Object.keys(candidate.collected_data ?? {})

  return (
    <div
      style={{
        background: 'rgba(30,41,59,0.65)',
        border: '1px solid rgba(245,158,11,0.35)',
        borderLeft: '3px solid #f59e0b',
        borderRadius: 12,
        padding: '1rem 1.125rem',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 0 0 0 rgba(245,158,11,0)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      }}
      className="candidate-card"
    >
      {/* Amber glow top-right */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 100,
          height: 100,
          background: 'radial-gradient(circle at top right, rgba(245,158,11,0.1), transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <span style={{ fontSize: 22, lineHeight: 1, flexShrink: 0 }}>{icon}</span>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '0.9375rem',
                fontWeight: 600,
                color: '#e2e8f0',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {candidate.suggested_title ||
                `${candidate.suggested_event_type.replace('_', ' ')} proposal`}
            </span>

            {/* Always-shown AI badge */}
            <span
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
          </div>

          <span
            style={{
              fontSize: '0.7rem',
              color: '#f59e0b',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {candidate.suggested_event_type.replace('_', ' ')}
          </span>
        </div>

        {/* Status badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            flexShrink: 0,
            background: isReady ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
            border: `1px solid ${isReady ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
            borderRadius: 999,
            padding: '2px 9px',
          }}
        >
          {isPending && (
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#f59e0b',
                display: 'inline-block',
                flexShrink: 0,
              }}
              className="pulse-amber"
            />
          )}
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              color: isReady ? '#6ee7b7' : '#fcd34d',
            }}
          >
            {STATUS_LABEL[candidate.status]}
          </span>
        </div>
      </div>

      {/* ── Customer ID ── */}
      <div style={{ marginTop: 10 }}>
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
          👤 {candidate.customer_id.slice(0, 8)}…
        </span>
      </div>

      {/* ── Collected data ── */}
      {collectedKeys.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <p
            style={{
              fontSize: '0.7rem',
              color: '#94a3b8',
              marginBottom: 6,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Collected
          </p>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {collectedKeys.map((k) => (
              <span
                key={k}
                style={{
                  fontSize: '0.7rem',
                  background: 'rgba(16,185,129,0.08)',
                  border: '1px solid rgba(16,185,129,0.2)',
                  borderRadius: 999,
                  padding: '2px 8px',
                  color: '#6ee7b7',
                }}
              >
                ✓ {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Missing fields ── */}
      {candidate.missing_fields.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <p
            style={{
              fontSize: '0.7rem',
              color: '#94a3b8',
              marginBottom: 6,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Missing
          </p>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {candidate.missing_fields.map((f) => (
              <span
                key={f}
                style={{
                  fontSize: '0.7rem',
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.25)',
                  borderRadius: 999,
                  padding: '2px 8px',
                  color: '#fca5a5',
                }}
              >
                ✕ {f.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Actions ── */}
      {(onPromote || onAbandon) && (
        <div
          style={{
            display: 'flex',
            gap: 6,
            marginTop: 12,
            borderTop: '1px solid rgba(255,255,255,0.06)',
            paddingTop: 10,
          }}
        >
          {onPromote && (
            <button
              onClick={() => onPromote(candidate.id)}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '5px 14px',
                borderRadius: 6,
                border: '1px solid rgba(16,185,129,0.4)',
                background: 'rgba(16,185,129,0.15)',
                color: '#6ee7b7',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              🚀 Promote to Event
            </button>
          )}
          {onAbandon && (
            <button
              onClick={() => onAbandon(candidate.id)}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                padding: '5px 14px',
                borderRadius: 6,
                border: '1px solid rgba(107,114,128,0.3)',
                background: 'rgba(107,114,128,0.08)',
                color: '#9ca3af',
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
            >
              Abandon
            </button>
          )}
        </div>
      )}

      <style>{`
        .candidate-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 32px rgba(245, 158, 11, 0.12);
        }
      `}</style>
    </div>
  )
}

export default CandidateCard

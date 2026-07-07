import api from './client'
import type {
  ScheduledEvent,
  ScheduledEventSummary,
  EventPage,
  ScheduleOverview,
  SchedulingCandidate,
  EventAuditEntry,
  CustomerAvailabilityPreferences,
} from '../types'

// ── Events ──────────────────────────────────────────────────────────────────

export const fetchEvents = (params?: {
  status?: string
  event_type?: string
  assigned_to?: string
  customer_id?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}) => api.get<EventPage>('/scheduling/events', { params }).then((r) => r.data)

export const fetchEventDetail = (id: string) =>
  api.get<ScheduledEvent>(`/scheduling/events/${id}`).then((r) => r.data)

export const createEvent = (data: {
  event_type: string
  title: string
  description?: string
  scheduled_for?: string
  duration_minutes?: number
  priority?: string
  metadata?: Record<string, unknown>
  customer_id?: string
  assigned_to?: string
  assignment_strategy?: string
}) => api.post<ScheduledEvent>('/scheduling/events', data).then((r) => r.data)

export const updateEvent = (
  id: string,
  data: {
    title?: string
    description?: string
    scheduled_for?: string
    duration_minutes?: number
    priority?: string
    metadata?: Record<string, unknown>
  },
) => api.put<ScheduledEvent>(`/scheduling/events/${id}`, data).then((r) => r.data)

export const confirmEvent = (id: string) =>
  api.post<ScheduledEvent>(`/scheduling/events/${id}/confirm`).then((r) => r.data)

export const startEvent = (id: string) =>
  api.post<ScheduledEvent>(`/scheduling/events/${id}/start`).then((r) => r.data)

export const completeEvent = (id: string) =>
  api.post<ScheduledEvent>(`/scheduling/events/${id}/complete`).then((r) => r.data)

export const cancelEvent = (id: string, reason?: string) =>
  api.post<ScheduledEvent>(`/scheduling/events/${id}/cancel`, { reason }).then((r) => r.data)

export const rescheduleEvent = (
  id: string,
  data: {
    new_scheduled_for: string
    duration_minutes?: number
    reason?: string
  },
) => api.post<ScheduledEvent>(`/scheduling/events/${id}/reschedule`, data).then((r) => r.data)

export const assignEvent = (
  id: string,
  data: {
    user_id: string
    strategy?: string
    override_conflicts?: boolean
  },
) => api.post<ScheduledEvent>(`/scheduling/events/${id}/assign`, data).then((r) => r.data)

export const fetchEventAuditLog = (id: string) =>
  api.get<EventAuditEntry[]>(`/scheduling/events/${id}/audit-log`).then((r) => r.data)

// ── Candidates ───────────────────────────────────────────────────────────────

export const fetchCandidates = () =>
  api.get<SchedulingCandidate[]>('/scheduling/candidates').then((r) => r.data)

export const fetchCandidateDetail = (id: string) =>
  api.get<SchedulingCandidate>(`/scheduling/candidates/${id}`).then((r) => r.data)

export const promoteCandidate = (
  id: string,
  data?: {
    title?: string
    scheduled_for?: string
    assigned_to?: string
  },
) =>
  api
    .post<ScheduledEvent>(`/scheduling/candidates/${id}/promote`, data || {})
    .then((r) => r.data)

export const abandonCandidate = (id: string) =>
  api.post<void>(`/scheduling/candidates/${id}/abandon`).then((r) => r.data)

// ── Schedule views ───────────────────────────────────────────────────────────

export const fetchTodaySchedule = () =>
  api.get<ScheduledEvent[]>('/scheduling/schedule/today').then((r) => r.data)

export const fetchUpcomingSchedule = (days = 7) =>
  api
    .get<ScheduledEvent[]>('/scheduling/schedule/upcoming', { params: { days } })
    .then((r) => r.data)

export const fetchScheduleOverview = () =>
  api.get<ScheduleOverview>('/scheduling/schedule/overview').then((r) => r.data)

// ── Customer scheduling ───────────────────────────────────────────────────────

export const fetchCustomerEvents = (customerId: string) =>
  api.get<ScheduledEvent[]>(`/scheduling/customers/${customerId}/events`).then((r) => r.data)

export const fetchCustomerAvailability = (customerId: string) =>
  api
    .get<CustomerAvailabilityPreferences>(`/scheduling/customers/${customerId}/availability`)
    .then((r) => r.data)

export const updateCustomerAvailability = (
  customerId: string,
  data: Partial<CustomerAvailabilityPreferences>,
) =>
  api
    .put<CustomerAvailabilityPreferences>(
      `/scheduling/customers/${customerId}/availability`,
      data,
    )
    .then((r) => r.data)

export type { ScheduledEventSummary }

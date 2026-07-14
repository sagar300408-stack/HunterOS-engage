import { api } from './dashboard'
import type { 
  FollowUpQueuePage, 
  FollowUpQueueDetail, 
  FollowUpOverviewStats,
  LeadHealthSummary,
  SalesTimelineEntry
} from '../types'

export const fetchFollowUpOverview = async (): Promise<FollowUpOverviewStats> => {
  const { data } = await api.get('/followups/overview')
  return data
}

export const fetchFollowUpQueue = async (
  status?: string, 
  priority?: string, 
  page = 1, 
  pageSize = 50
): Promise<FollowUpQueuePage> => {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  if (priority) params.append('priority', priority)
  params.append('page', page.toString())
  params.append('page_size', pageSize.toString())
  
  const { data } = await api.get(`/followups/queue?${params.toString()}`)
  return data
}

export const fetchFollowUpDetail = async (id: string): Promise<FollowUpQueueDetail> => {
  const { data } = await api.get(`/followups/queue/${id}`)
  return data
}

export const pauseFollowUp = async (id: string): Promise<void> => {
  await api.post(`/followups/queue/${id}/pause`)
}

export const resumeFollowUp = async (id: string): Promise<void> => {
  await api.post(`/followups/queue/${id}/resume`)
}

export const cancelFollowUp = async (id: string, reason: string): Promise<void> => {
  await api.post(`/followups/queue/${id}/cancel`, { reason })
}

export const sendFollowUpNow = async (id: string): Promise<void> => {
  await api.post(`/followups/queue/${id}/send-now`)
}

export const updateFollowUpMessage = async (id: string, message: string): Promise<void> => {
  await api.put(`/followups/queue/${id}/message`, { message })
}

export const rescheduleFollowUp = async (id: string, scheduledFor: string): Promise<void> => {
  await api.put(`/followups/queue/${id}/reschedule`, { scheduled_for: scheduledFor })
}

// Customer specifics
export const fetchLeadHealth = async (customerId: string): Promise<LeadHealthSummary> => {
  const { data } = await api.get(`/followups/customer/${customerId}/health`)
  return data
}

export const fetchSalesTimeline = async (customerId: string, limit = 50): Promise<SalesTimelineEntry[]> => {
  const { data } = await api.get(`/followups/customer/${customerId}/timeline?limit=${limit}`)
  return data
}

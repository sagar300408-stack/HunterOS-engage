import api from './client'
import type {
  OverviewMetrics, ConversationPage, ConversationDetail,
  CustomerPage, CustomerProfile, LeadPipeline,
  AnalyticsData, SystemHealth, ActivityEvent,
  QueueStatus, AuditLog, SearchResults,
} from '../types'

export const fetchOverview = () =>
  api.get<OverviewMetrics>('/dashboard/overview').then(r => r.data)

export const fetchConversations = (params?: {
  search?: string; buying_stage?: string; page?: number; page_size?: number
}) => api.get<ConversationPage>('/dashboard/conversations', { params }).then(r => r.data)

export const fetchConversationDetail = (id: string) =>
  api.get<ConversationDetail>(`/dashboard/conversations/${id}`).then(r => r.data)

export const fetchCustomers = (params?: {
  search?: string; buying_stage?: string; status?: string; page?: number; page_size?: number
}) => api.get<CustomerPage>('/dashboard/customers', { params }).then(r => r.data)

export const fetchCustomerProfile = (id: string) =>
  api.get<CustomerProfile>(`/dashboard/customers/${id}`).then(r => r.data)

export const updateCustomer = (id: string, data: Partial<{ name: string; email: string; notes: string; status: string }>) =>
  api.put(`/dashboard/customers/${id}`, data)

export const fetchLeads = () =>
  api.get<LeadPipeline>('/dashboard/leads').then(r => r.data)

export const updateLeadStage = (customer_id: string, buying_stage: string, reason?: string) =>
  api.put(`/dashboard/leads/${customer_id}/stage`, { buying_stage, reason })

export const fetchAnalytics = (params?: { date_from?: string; date_to?: string }) =>
  api.get<AnalyticsData>('/dashboard/analytics', { params }).then(r => r.data)

export const fetchSystemHealth = () =>
  api.get<SystemHealth>('/dashboard/system-health').then(r => r.data)

export const fetchActivity = (limit = 50) =>
  api.get<ActivityEvent[]>('/dashboard/activity', { params: { limit } }).then(r => r.data)

export const fetchQueue = () =>
  api.get<QueueStatus>('/dashboard/queue').then(r => r.data)

export const fetchAuditLog = (limit = 100) =>
  api.get<AuditLog[]>('/dashboard/audit-log', { params: { limit } }).then(r => r.data)

export const searchEverything = (q: string, limit = 30) =>
  api.get<SearchResults>('/dashboard/search', { params: { q, limit } }).then(r => r.data)

export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password }).then(r => r.data)

export const fetchMe = () =>
  api.get('/auth/me').then(r => r.data)

// All TypeScript types matching the backend Pydantic schemas

export interface MetricCard {
  label: string
  value: number
  unit?: string
  trend?: number
  trend_direction?: 'up' | 'down' | 'neutral'
}

export interface OverviewMetrics {
  active_conversations: MetricCard
  total_customers: MetricCard
  new_leads_today: MetricCard
  qualified_leads: MetricCard
  purchase_ready: MetricCard
  avg_response_time_ms: MetricCard
  ai_success_rate: MetricCard
  memory_updates_today: MetricCard
  total_cost_today_usd: MetricCard
  upcoming_events?: MetricCard
  pending_callbacks?: MetricCard
  pending_followups?: MetricCard
}

export interface IntentSummary {
  detected_intent: string
  confidence: number
  urgency: string
  buying_stage?: string
  budget?: string
  budget_confidence?: number
  timeline?: string
  interest?: string
  location?: string
  next_action?: string
  reasoning?: string
  memory_influenced?: string
  detected_keywords?: string[]
  created_at: string
}

export interface PipelineEvent {
  id: string
  step: string
  status: string
  duration_ms?: number
  payload?: Record<string, unknown>
  created_at: string
}

export interface MessageDetail {
  id: string
  direction: 'incoming' | 'outgoing'
  content: string
  timestamp: string
  intent?: IntentSummary
  ai_model?: string
  total_tokens?: number
  latency_ms?: number
  estimated_cost_usd?: number
}

export interface ConversationSummary {
  id: string
  customer_id?: string
  customer_name?: string
  customer_phone: string
  last_message?: string
  last_message_direction?: string
  last_activity?: string
  message_count: number
  detected_intent?: string
  buying_stage?: string
  urgency?: string
  created_at: string
}

export interface ConversationPage {
  items: ConversationSummary[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface ConversationDetail {
  id: string
  customer_id?: string
  customer_name?: string
  customer_phone: string
  created_at: string
  messages: MessageDetail[]
  pipeline_events: PipelineEvent[]
}

export interface MemorySummary {
  summary?: string
  budget?: { value?: string; confidence?: number }
  timeline?: { value?: string; confidence?: number }
  preferred_location?: { value?: string; confidence?: number }
  interests?: string[]
  message_count: number
  last_updated?: string
}

export interface CustomerSummary {
  id: string
  name?: string
  phone: string
  email?: string
  status: string
  buying_stage?: string
  qualification_score?: number
  qualification_grade?: string
  last_interaction?: string
  created_at: string
}

export interface CustomerPage {
  items: CustomerSummary[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface CustomerProfile {
  id: string
  name?: string
  phone: string
  email?: string
  status: string
  buying_stage?: string
  notes?: string
  preferred_language: string
  created_at: string
  last_interaction?: string
  memory?: MemorySummary
  recent_intents: IntentSummary[]
  conversation_count: number
  qualification?: {
    score: number
    grade: string
    qualified: boolean
    urgency: string
    budget?: string
    timeline?: string
    next_action?: string
  }
}

export interface LeadCard {
  customer_id: string
  name?: string
  phone: string
  buying_stage: string
  urgency?: string
  budget?: string
  timeline?: string
  interest?: string
  qualification_score: number
  qualification_grade: string
  last_interaction?: string
}

export interface LeadPipeline {
  stages: Record<string, LeadCard[]>
}

export interface DailyMetric {
  date: string
  value: number
}

export interface IntentDistribution {
  intent: string
  count: number
  percentage: number
}

export interface CostMetrics {
  total_cost_usd: number
  avg_cost_per_conversation: number
  avg_cost_per_lead: number
  avg_cost_per_qualified_lead: number
  total_prompt_tokens: number
  total_completion_tokens: number
  avg_tokens_per_response: number
}

export interface AnalyticsData {
  date_from: string
  date_to: string
  conversations_per_day: DailyMetric[]
  leads_per_day: DailyMetric[]
  intent_distribution: IntentDistribution[]
  avg_response_time_per_day: DailyMetric[]
  cost_metrics: CostMetrics
}

export interface ServiceStatus {
  name: string
  status: 'online' | 'warning' | 'offline' | 'not_configured'
  latency_ms?: number
  uptime_pct?: number
  detail?: string
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'down'
  services: ServiceStatus[]
  checked_at: string
}

export interface ActivityEvent {
  id: string
  event_type: string
  description: string
  customer_name?: string
  customer_phone?: string
  metadata?: Record<string, unknown>
  created_at: string
}

export interface BackgroundJob {
  id: string
  job_type: string
  status: string
  run_count: number
  last_error?: string
  scheduled_at: string
  started_at?: string
  completed_at?: string
}

export interface QueueStatus {
  pending: number
  running: number
  completed_today: number
  failed: number
  jobs: BackgroundJob[]
}

export interface AuditLog {
  id: string
  action: string
  target_type: string
  target_id?: string
  user_email?: string
  payload?: Record<string, unknown>
  ip_address?: string
  created_at: string
}

export interface SearchHit {
  type: string
  id: string
  title: string
  subtitle?: string
  highlight?: string
  score: number
}

export interface SearchResults {
  query: string
  total: number
  hits: SearchHit[]
}

export interface User {
  id: string
  email: string
  full_name?: string
  role: string
  workspace_id: string
  created_at: string
  last_login?: string
}

export interface AuthState {
  token: string | null
  user: User | null
  role: string | null
  workspace_id: string | null
}

export interface WSEvent {
  event: string
  data: Record<string, unknown>
  timestamp: string
}

export type NavSection =
  | 'overview'
  | 'conversations'
  | 'customers'
  | 'leads'
  | 'schedule'
  | 'analytics'
  | 'activity'
  | 'queue'
  | 'system'
  | 'audit'
  | 'developer_tools'
  | 'followup'

// ── Phase 5: Scheduling Engine ─────────────────────────────────────────────

export type EventType = 'meeting' | 'site_visit' | 'callback' | 'followup' | 'reminder' | 'task'
export type EventStatus = 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'rescheduled'
export type EventPriority = 'high' | 'medium' | 'low'

export interface ScheduledEventSummary {
  id: string
  event_type: EventType
  title: string
  status: EventStatus
  priority: EventPriority
  scheduled_for?: string
  customer_id?: string
  assigned_to?: string
  created_by_ai: boolean
  created_at: string
}

export interface ScheduledEvent extends ScheduledEventSummary {
  workspace_id: string
  description?: string
  duration_minutes?: number
  conversation_id?: string
  assignment_strategy: string
  created_by?: string
  crm_synced: boolean
  metadata?: Record<string, unknown>
  follow_up_policy?: Record<string, unknown>
  allowed_transitions: string[]
  updated_at: string
  completed_at?: string
  cancelled_at?: string
}

export interface EventPage {
  items: ScheduledEventSummary[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface ScheduleOverview {
  total_events: number
  pending: number
  confirmed: number
  in_progress: number
  completed_today: number
  cancelled_today: number
  upcoming_7_days: number
  pending_callbacks: number
  pending_followups: number
  active_candidates: number
  events_by_type: Record<string, number>
}

export interface SchedulingCandidate {
  id: string
  workspace_id: string
  customer_id: string
  conversation_id?: string
  suggested_event_type: EventType
  suggested_title?: string
  status: 'pending_info' | 'ready' | 'promoted' | 'abandoned'
  missing_fields: string[]
  collected_data: Record<string, unknown>
  created_by_ai: boolean
  created_at: string
  updated_at: string
  promoted_event_id?: string
}

export interface EventAuditEntry {
  id: string
  actor_type: 'user' | 'ai' | 'system'
  actor_id?: string
  action: string
  from_status?: string
  to_status?: string
  payload?: Record<string, unknown>
  created_at: string
}

export interface ConflictResult {
  has_conflict: boolean
  conflicting_event_ids: string[]
  suggested_slots: string[]
}

export interface CustomerAvailabilityPreferences {
  id?: string
  customer_id: string
  preferred_time_of_day?: 'morning' | 'afternoon' | 'evening' | 'any'
  unavailable_days?: string[]
  preferred_meeting_mode?: 'in_person' | 'online' | 'phone' | 'any'
  timezone: string
  notes?: string
  updated_at?: string
}
// ── Phase 6 Follow-Up Engine ──────────────────────────────────────────────────

export interface LeadHealthSummary {
  score: number;
  band: 'Excellent' | 'Good' | 'Moderate' | 'At Risk' | 'Critical';
  reasons: string[];
  positive_signals: string[];
  recommendation?: string;
}

export interface SalesTimelineEntry {
  id: string;
  event_type: string;
  title: string;
  description?: string;
  created_at: string;
}

export interface FollowUpQueueSummary {
  id: string;
  customer_id: string;
  customer_name?: string;
  customer_phone?: string;
  status: 'scheduled' | 'executing' | 'sent' | 'cancelled' | 'paused' | 'replied';
  reason: string;
  strategy?: string;
  priority: 'high' | 'normal' | 'low';
  scheduled_for: string;
  human_paused: boolean;
  retry_count: number;
}

export interface FollowUpQueueDetail extends FollowUpQueueSummary {
  generated_message?: string;
  final_message?: string;
  channel: string;
  explainability_report?: any;
  confidence_score?: number;
  risk_score?: number;
  cancellation_reason?: string;
  created_at: string;
  updated_at: string;
  executed_at?: string;
  executions: any[];
}

export interface FollowUpOverviewStats {
  pending_followups: number;
  due_today: number;
  sent_today: number;
  failed_today: number;
  paused_needs_review: number;
  strategy_distribution: Record<string, number>;
}

export interface FollowUpQueuePage {
  items: FollowUpQueueSummary[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}
// ── Phase 6 Follow-Up Engine ──────────────────────────────────────────────────

export interface LeadHealthSummary {
  score: number;
  band: 'Excellent' | 'Good' | 'Moderate' | 'At Risk' | 'Critical';
  reasons: string[];
  positive_signals: string[];
  recommendation?: string;
}

export interface SalesTimelineEntry {
  id: string;
  event_type: string;
  title: string;
  description?: string;
  created_at: string;
}

export interface FollowUpQueueSummary {
  id: string;
  customer_id: string;
  customer_name?: string;
  customer_phone?: string;
  status: 'scheduled' | 'executing' | 'sent' | 'cancelled' | 'paused' | 'replied';
  reason: string;
  strategy?: string;
  priority: 'high' | 'normal' | 'low';
  scheduled_for: string;
  human_paused: boolean;
  retry_count: number;
}

export interface FollowUpQueueDetail extends FollowUpQueueSummary {
  generated_message?: string;
  final_message?: string;
  channel: string;
  explainability_report?: any;
  confidence_score?: number;
  risk_score?: number;
  cancellation_reason?: string;
  created_at: string;
  updated_at: string;
  executed_at?: string;
  executions: any[];
}

export interface FollowUpOverviewStats {
  pending_followups: number;
  due_today: number;
  sent_today: number;
  failed_today: number;
  paused_needs_review: number;
  strategy_distribution: Record<string, number>;
}

export interface FollowUpQueuePage {
  items: FollowUpQueueSummary[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

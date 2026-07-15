# HunterOS Engage — Phase 7 Architecture
## Event-Driven AI Operating Platform

> **Document Type:** Architectural Specification  
> **Status:** Approved for Implementation  
> **Version:** 1.0  
> **Audience:** Senior Software Architects, Engineering Leads, Future Contributors  
> **Supersedes:** All prior inter-subsystem communication patterns  
> **Effective From:** Phase 7 onward — all future phases must comply

---

## Table of Contents

1. [Vision](#1-vision)
2. [Problem Statement](#2-problem-statement)
3. [Core Philosophy](#3-core-philosophy)
4. [Event-Driven Architecture](#4-event-driven-architecture)
5. [Event Lifecycle](#5-event-lifecycle)
6. [Event Model](#6-event-model)
7. [Event Categories](#7-event-categories)
8. [Event Publisher Contract](#8-event-publisher-contract)
9. [Event Consumers](#9-event-consumers)
10. [Event Store](#10-event-store)
11. [Activity Timeline](#11-activity-timeline)
12. [AI Explainability](#12-ai-explainability)
13. [Live Event Streaming](#13-live-event-streaming)
14. [Extensibility](#14-extensibility)
15. [Folder Structure](#15-folder-structure)
16. [Deliverables](#16-deliverables)
17. [Success Criteria](#17-success-criteria)

---

## 1. Vision

### 1.1 What HunterOS Has Become

HunterOS began as a conversational AI SDR application. Today, after six phases of engineering, it is a multi-subsystem intelligent platform containing:

- **Conversation Intelligence Engine** — processes inbound messages, runs AI reasoning, and generates responses
- **Scheduling Engine** — handles meeting lifecycle, conflict resolution, and calendar coordination
- **Follow-up Intelligence Engine** — orchestrates outreach sequences, health scoring, and sales memory
- **CRM Synchronization** — maintains data consistency with external customer relationship systems
- **Analytics Engine** — aggregates operational metrics across all domains
- **Dashboard** — provides real-time visibility into platform health and sales activity
- **Authentication System** — controls workspace-level access and identity
- **Audit Trail** — records every significant platform decision for compliance and traceability

Each of these subsystems has grown independently. Each solves a distinct domain problem. Each has its own models, services, and business logic.

The natural consequence of this growth is an increasingly tangled web of direct dependencies. Services call other services. Engines update dashboards. Follow-up logic reaches into conversation state. Analytics are written directly by the subsystems that generate the data.

**Phase 7 is not a feature. It is an architectural reckoning.**

### 1.2 Why an Event-Driven Architecture

As HunterOS scales toward enterprise-grade capabilities — multi-agent AI systems, revenue intelligence, voice agents, proposal generation, and executive reporting — the current communication model will become its primary engineering bottleneck.

Direct communication between subsystems creates the following structural problems:

**Coupling proliferates exponentially.** Every new subsystem that needs to know about a business event must be individually wired to every source that produces it. Ten subsystems interacting with ten others creates up to one hundred dependency edges. Adding an eleventh requires updating potentially ten existing systems.

**Change becomes dangerous.** When subsystem A directly calls subsystem B, modifying either one risks breaking the other. Engineers must trace the full call graph before making safe changes. This slows delivery and increases regression risk.

**New intelligence cannot plug in cleanly.** A future AI agent that needs to observe every customer interaction currently has no clean integration point. It would need to be manually injected into each pipeline stage that produces relevant events.

**Observability is ad hoc.** Without a uniform event stream, understanding what the platform actually did at any given moment requires stitching together logs from multiple services with inconsistent formats.

**Replay and auditability are impossible.** If an enterprise customer demands a complete reconstruction of what happened during a sales engagement, there is no reliable mechanism to provide it when the data is scattered across isolated service calls.

An Event-Driven Architecture addresses all of these problems simultaneously by introducing a single, authoritative communication layer: **the Event Bus**.

### 1.3 Phase 7 as an Architectural Milestone

Previous phases added business capabilities. Phase 7 establishes the **communication infrastructure** upon which every future business capability will be built.

This is the equivalent of installing a city's road network before building the neighborhoods. The roads do not perform any business function themselves — they enable all future construction to happen efficiently, independently, and without interfering with one another.

From Phase 7 onward, HunterOS is not a collection of services that call each other. It is a collection of **independent intelligent nodes** that publish and consume business events through a shared backbone.

---

## 2. Problem Statement

### 2.1 The Current Communication Model

In the existing architecture, subsystems communicate through direct function calls, service imports, and shared database writes. A simplified view of current coupling:

```
Conversation Pipeline
    │
    ├──► Calls FollowUp.schedule_followup()
    ├──► Calls FollowUp.upsert_health_score()
    ├──► Calls Analytics.record_message()
    ├──► Calls CRM.sync_customer()
    └──► Writes directly to Dashboard models

FollowUp Engine
    │
    ├──► Reads Conversation state directly
    ├──► Calls CRM.update_last_contact()
    └──► Updates Dashboard metrics directly

Scheduling Engine
    │
    ├──► Calls Notification service directly
    ├──► Writes to Audit log directly
    └──► Updates Analytics counters directly
```

Every arrow in this diagram is a direct dependency. Every dependency is a coupling point that must be maintained, tested, and evolved in lockstep.

### 2.2 Why This Model Fails at Scale

**The N×M dependency problem.** As subsystems grow from six to twelve, direct communication edges grow from a manageable number to an unmaintainable mesh. Every new AI capability that requires awareness of business events must be inserted into every relevant call site manually.

**Publisher knows too much.** The Conversation Engine currently must know that the Follow-up Engine exists, that the Analytics Engine exists, and that the Dashboard must be updated. This is a violation of separation of concerns. The Conversation Engine's responsibility is conversation — not orchestrating downstream reactions.

**Temporal coupling.** When one subsystem directly calls another, both must be available and correct at the same moment. If the Analytics service is slow, it slows the Conversation Engine. If it throws, it may corrupt the pipeline.

**Testing becomes a system-of-systems problem.** To unit test the Conversation Engine, you must mock the Follow-up Engine, the CRM synchronizer, the Analytics writer, and the Dashboard updater. The test setup describes inter-system relationships, not business logic.

**Audit and replay are structurally absent.** There is no single place where "what happened" is recorded as a first-class concept. Reconstructing a customer's journey requires joining across multiple service logs and database tables with no guaranteed ordering or completeness.

**AI agents have no clean integration surface.** Future intelligent agents — research agents, proposal generators, forecasting models — need to observe platform events and react intelligently. In a direct-call model, there is no observation surface. Each agent would need to be surgically inserted into dozens of call sites.

### 2.3 The Inevitable Consequence

Without Phase 7, HunterOS's future capability phases will slow down with each addition. Engineers will spend increasingly more time managing inter-subsystem dependencies than building intelligence. The platform will develop a debt ceiling that constrains its potential.

Phase 7 removes that ceiling permanently.

---

## 3. Core Philosophy

These principles are **non-negotiable**. They define the architectural identity of HunterOS from Phase 7 onward. Every engineering decision made in future phases must be evaluated against them.

---

### Principle 1 — Publish, Do Not Notify Directly

When something significant happens in the system, the responsible subsystem publishes a business event. It does not call downstream services. It does not update dashboards. It does not trigger notifications. It announces that something happened and relinquishes control.

> **Wrong:** `conversation_engine.complete() → analytics.record() → dashboard.update() → audit.log()`  
> **Right:** `conversation_engine.complete() → publish(ConversationCompleted)`

---

### Principle 2 — Consumers Decide What to Do

The Event Bus does not route events to specific destinations. Events are published into the bus. Consumers decide independently whether a given event is relevant to them and what action to take in response.

A publisher must never assume what consumers exist. A publisher must never encode consumer-specific logic. A publisher publishes the truth of what happened. Consumers interpret that truth according to their own domain rules.

---

### Principle 3 — Events Are Immutable Facts

An event is a record of something that occurred. It describes the past. It cannot be modified, retracted, or overwritten. An event is always in the past tense:

- `CustomerReplied` — not `CustomerIsReplying`
- `MeetingScheduled` — not `ScheduleMeeting`
- `FollowUpExecuted` — not `ExecuteFollowUp`
- `AIDecisionMade` — not `MakeAIDecision`

Commands request future action. Events record past fact. HunterOS's Event Bus carries events, not commands.

---

### Principle 4 — Every Significant Business Action Becomes an Event

If an action has any business consequence — if any part of the system might care about it now or in the future — it must be represented as an event. Significance is defined broadly. When in doubt, publish.

Events are cheap. Missing an important event is expensive.

---

### Principle 5 — Publishers Never Know Consumers

A publisher does not import, reference, or have any runtime knowledge of its consumers. The dependency graph is strictly: subsystem → Event Bus. Never: subsystem → subsystem.

This principle is the foundation of the entire architecture. Violating it reintroduces coupling through the back door.

---

### Principle 6 — New Consumers Require Zero Publisher Changes

When a new AI agent, analytics consumer, audit logger, or notification handler is added to the platform, no existing publisher changes. No existing code is modified. No existing tests change. The new consumer registers itself with the Event Bus and begins receiving the events it needs.

This principle defines extensibility. If adding a consumer requires touching a publisher, the architecture has been violated.

---

### Principle 7 — The Event Bus Is a Platform Capability

The Event Bus does not belong to any business domain. It does not belong to Conversations, Scheduling, Follow-up, CRM, Analytics, or the Dashboard. It belongs to the platform itself. It is infrastructure in the same way that the database, the web server, and the logging system are infrastructure.

Any subsystem may publish to it. Any subsystem may consume from it. No subsystem owns it.

---

### Principle 8 — Event Integration is Mandatory for New Subsystems

Every new subsystem introduced after Phase 7 must integrate by publishing and/or subscribing to events. Direct subsystem-to-subsystem communication is prohibited unless there is a compelling architectural reason.

---

## 4. Event-Driven Architecture

### 4.1 Architectural Topology

HunterOS's Phase 7 architecture follows a **Publish-Subscribe Bus Topology**. Every subsystem is an independent node connected to the Event Bus. Publishers emit events. Consumers receive events. The bus mediates all communication.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         HUNTEROS PLATFORM LAYER                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐          ║
║   │  Conversation   │   │   Scheduling    │   │    Follow-up    │          ║
║   │    Engine       │   │    Engine       │   │    Engine       │          ║
║   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘          ║
║            │  publish            │  publish            │  publish           ║
║            ▼                     ▼                     ▼                    ║
║   ┌──────────────────────────────────────────────────────────────────────┐  ║
║   │                         EVENT BUS                                    │  ║
║   │                    (Platform Infrastructure)                         │  ║
║   └───────────────────────────────────────┬──────────────────────────────┘  ║
║            ▲                     ▲         │ distribute                      ║
║            │  publish            │  publish ▼                               ║
║   ┌─────────────────┐   ┌─────────┴───────┐                                 ║
║   │      CRM        │   │    AI Agents    │                                  ║
║   │  Synchronizer   │   │    (Future)     │                                  ║
║   └─────────────────┘   └─────────────────┘                                 ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                         CONSUMER LAYER                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ ║
║   │  Activity  │ │ Analytics  │ │  Audit     │ │Notification│ │WebSocket │ ║
║   │  Timeline  │ │  Engine    │ │  Trail     │ │  Service   │ │Streaming │ ║
║   └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ ║
║                                                                              ║
║   ┌────────────┐ ┌────────────┐ ┌────────────┐                             ║
║   │ Dashboard  │ │ Future AI  │ │  Revenue   │                             ║
║   │  Updater   │ │   Agents   │ │Intelligence│                             ║
║   └────────────┘ └────────────┘ └────────────┘                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 4.2 The Event Bus Role

The Event Bus is the sole communication medium between all HunterOS subsystems. Its responsibilities are:

1. **Receive** events published by any subsystem
2. **Store** all events in the immutable Event Store
3. **Route** events to all registered consumers for each event category
4. **Stream** events to live consumers (WebSocket, SSE)
5. **Provide** event replay and historical access

The Event Bus has no business logic of its own. It does not interpret events. It does not make routing decisions based on event content. It distributes everything it receives to all registered consumers for each event type.

### 4.3 How Publishers Interact with the Bus

A publisher's interaction with the Event Bus is a single operation: `publish(event)`. This call is the entire publisher contract. Everything that happens after publication is outside the publisher's knowledge and responsibility.

The publish operation must be:
- **Non-blocking** — publishers must not wait for consumers to complete
- **Fire-and-forget** — publishers must not receive consumer responses
- **Failure-isolated** — a consumer failure must never propagate back to the publisher

### 4.4 How Consumers Interact with the Bus

A consumer declares its interest in one or more event categories or specific event types. When the Event Bus receives a matching event, it delivers it to all registered consumers. Each consumer processes the event independently.

Consumer registration happens at platform startup. Consumers are never registered or deregistered at runtime in response to business events.

### 4.5 Why This Dramatically Reduces Coupling

In the pre-Phase-7 architecture, adding a new consumer of "customer reply" events required:
1. Finding every place a customer reply could be processed
2. Importing the new consumer into each of those locations
3. Adding a direct call to the new consumer
4. Testing all modified locations

In the Phase 7 architecture, adding a new consumer of `CustomerReplied` events requires:
1. Creating the new consumer
2. Registering it with the Event Bus for `CustomerReplied` events
3. Testing the consumer in isolation

No existing code changes. No existing tests change. The publisher does not know the consumer exists.

---

## 5. Event Lifecycle

### 5.1 Complete Lifecycle Description

Every business event in HunterOS follows the same lifecycle from origination to consumption. The following describes this lifecycle in full:

```
STAGE 1 — BUSINESS ACTION OCCURS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A customer sends a WhatsApp message.
The Conversation Engine receives and processes it.
A reply is generated and sent.

   ↓

STAGE 2 — EVENT CONSTRUCTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The publisher constructs an immutable event object.
Fields are populated: event_id, occurred_at, workspace_id,
customer_id, conversation_id, category, source, payload.
The event represents exactly what happened — nothing more.

   ↓

STAGE 3 — PUBLICATION
━━━━━━━━━━━━━━━━━━━━━━
The publisher calls event_bus.publish(event).
The publisher's responsibility ends here.
The publisher has no further involvement in this event's journey.

   ↓

STAGE 4 — PERSISTENCE
━━━━━━━━━━━━━━━━━━━━━━
The Event Bus writes the event to the immutable Event Store.
This write happens before consumer delivery.
The event is now a permanent, auditable record of the platform's history.

   ↓

STAGE 5 — DISTRIBUTION
━━━━━━━━━━━━━━━━━━━━━━━
The Event Bus identifies all consumers registered for this event category.
Each consumer is invoked independently.
Consumer failures are isolated — one failing consumer does not affect others.

   ↓

STAGE 6 — CONSUMPTION
━━━━━━━━━━━━━━━━━━━━━━
Each consumer processes the event according to its own domain logic:

  Activity Timeline Consumer:
    Appends a timeline entry for the customer's engagement history.

  Analytics Consumer:
    Increments conversation metrics, response time counters, engagement scores.

  Dashboard Consumer:
    Updates real-time workspace activity indicators.

  Audit Trail Consumer:
    Records the event in the compliance-grade audit log with full context.

  Notification Consumer:
    Evaluates notification rules and dispatches alerts if applicable.

  WebSocket Streaming Consumer:
    Pushes the event to connected frontend clients for live updates.

  Future AI Agent Consumers:
    Observe the event and decide whether to trigger intelligent actions.

   ↓

STAGE 7 — COMPLETION
━━━━━━━━━━━━━━━━━━━━━
All consumers have processed (or failed safely with logging).
The event remains permanently stored in the Event Store.
It is available for replay, audit queries, AI training, and timeline reconstruction.
```

### 5.2 Concrete Example — Customer Reply Flow

```
Customer sends "Yes, I'd like to book a demo"
         │
         ▼
┌─────────────────────────────────┐
│      Conversation Engine        │
│                                 │
│  1. Receives webhook payload    │
│  2. Processes intent            │
│  3. Generates AI response       │
│  4. Sends WhatsApp reply        │
│  5. Constructs CustomerReplied  │
│     event with full context     │
│  6. publish(CustomerReplied)    │
└─────────────┬───────────────────┘
              │ publish
              ▼
┌─────────────────────────────────┐
│           EVENT BUS             │
│                                 │
│  1. Assigns sequence number     │
│  2. Persists to Event Store     │
│  3. Routes to all consumers     │
└──┬──────┬──────┬──────┬─────────┘
   │      │      │      │
   ▼      ▼      ▼      ▼
Timeline  Analytics  Audit  Notifications
Consumer  Consumer   Trail  Consumer
                            │
                            ▼
                    Dashboard    WebSocket    FollowUp     Future
                    Consumer     Streaming    Consumer     AI Agent
```

---

## 6. Event Model

### 6.1 Universal Event Structure

Every event in HunterOS, regardless of which subsystem produces it, must conform to the Universal Event Model. This model exists at the platform level and belongs to the Event Infrastructure domain.

The Universal Event is composed of three layers:
- **Identity Layer** — uniquely identifies and traces the event
- **Context Layer** — places the event in its business context
- **Content Layer** — describes what actually happened and carries domain-specific data

---

### 6.2 Identity Layer Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | A globally unique identifier for this specific event instance. Generated at construction time. Used for deduplication, idempotency, and cross-system correlation. |
| `schema_version` | Integer | The version of the event schema. Starts at 1. Incremented when the event structure changes. Allows consumers to handle schema evolution gracefully. |
| `occurred_at` | UTC DateTime | The precise moment the business action occurred. Set by the publisher at construction time. Not the time the event was received by the bus. |
| `correlation_id` | UUID | A shared identifier that links all events produced by a single end-to-end operation. If a customer message triggers five downstream events, all five share the same correlation_id. Enables full request tracing. |
| `causation_id` | UUID | The event_id of the event that directly caused this event to be produced. Enables causal chain reconstruction. If Event A causes Event B, then Event B's causation_id equals Event A's event_id. |

---

### 6.3 Context Layer Fields

| Field | Type | Description |
|-------|------|-------------|
| `workspace_id` | UUID | The workspace (tenant) in which this event occurred. All events are workspace-scoped. Required for multi-tenant isolation of event history and analytics. |
| `customer_id` | UUID (nullable) | The customer this event relates to. Null only for workspace-level or platform-level events. |
| `lead_id` | UUID (nullable) | The lead record associated with this event, if applicable. |
| `conversation_id` | UUID (nullable) | The conversation this event occurred within, if applicable. |
| `actor_type` | Enum | Who or what produced this event. One of: `ai_agent`, `human_agent`, `system`, `customer`, `external_integration`. |
| `actor_id` | String (nullable) | The specific identity of the actor. For AI, this is the model identifier. For human agents, the user ID. For system events, the service name. |
| `source_subsystem` | String | The name of the subsystem that published this event. Examples: `conversation_engine`, `scheduling_engine`, `followup_engine`. Used for routing, debugging, and attribution. |

---

### 6.4 Content Layer Fields

| Field | Type | Description |
|-------|------|-------------|
| `category` | Enum | The high-level business category this event belongs to. See Section 7 for the full category taxonomy. |
| `event_type` | String | The specific name of the event within its category. Examples: `customer.replied`, `meeting.scheduled`, `followup.executed`. Always past tense. |
| `payload` | JSON Object | The domain-specific data for this event. Content varies by event type. Defined per-event by the publishing subsystem. Should contain the minimum information needed to make the event self-describing. |
| `metadata` | JSON Object | Non-domain operational metadata. Examples: processing duration, external API identifiers, feature flags active at the time of the event, channel information. Does not contain business data. |

---

### 6.5 AI Decision Fields

These fields are populated exclusively by events produced by AI reasoning processes. They are null for non-AI events.

| Field | Type | Description |
|-------|------|-------------|
| `ai_model_version` | String (nullable) | The specific model identifier used to produce this decision. Examples: `gpt-4o-2024-11-20`, `hunter-intent-v3`. Required for AI events. |
| `ai_reason` | String (nullable) | A human-readable explanation of why the AI made this decision. Written in plain language for enterprise customers. |
| `ai_confidence` | Float (nullable) | A normalized confidence score between 0.0 and 1.0 indicating the AI's certainty in its decision. |
| `ai_evidence` | JSON Array (nullable) | The specific data points, signals, or context fragments the AI used to arrive at its decision. |
| `ai_inputs` | JSON Object (nullable) | A structured representation of the inputs provided to the AI model. |
| `ai_outputs` | JSON Object (nullable) | A structured representation of the outputs the AI model produced. |

---

### 6.6 Why Every Field Exists

**event_id** exists because events are stored and must be individually addressable. Without it, deduplication is impossible.

**schema_version** exists because event schemas will evolve. Without versioning, a consumer cannot distinguish between a v1 and v2 `MeetingScheduled` event, and schema changes would break all consumers simultaneously.

**occurred_at** exists because events must be orderable by when they happened in the business domain, not when they were processed by infrastructure.

**correlation_id** exists because debugging requires the ability to trace a single customer interaction across every event it produced in every subsystem.

**causation_id** exists because AI systems and audit systems need to understand causal relationships between events, not just temporal ordering.

**workspace_id** exists because HunterOS is a multi-tenant platform. Every consumer must be able to scope its processing to a single workspace without knowing about other tenants.

**actor_type and actor_id** exist because auditability requires knowing whether a decision was made by a human, the AI, or an automated system process. This is non-negotiable for enterprise compliance.

**source_subsystem** exists because operators need to understand which part of the platform generated an event when debugging or monitoring.

**category and event_type** exist because consumers register interest by category. Granular event_type allows consumers to further filter without receiving and discarding irrelevant events.

**payload** exists because an event without domain content is not useful. The payload makes the event self-describing.

**metadata** exists because operational context (latency, external IDs, debug flags) should never pollute the business payload but must remain accessible.

**AI fields** exist because enterprises require the ability to audit every AI decision. Without these fields, HunterOS cannot be sold to regulated industries or enterprise customers with AI governance requirements.

---

## 7. Event Categories

The following taxonomy defines the official event categories for HunterOS. Every event published to the Event Bus must belong to exactly one category.

---

### `CUSTOMER`
Events concerning the customer entity itself.

| Event Type | Description |
|------------|-------------|
| `customer.created` | A new customer record was created in the system |
| `customer.profile_updated` | Customer demographic or profile data was modified |
| `customer.replied` | A customer sent a message on any channel |
| `customer.qualified` | A customer was assessed as meeting qualification criteria |
| `customer.disqualified` | A customer no longer meets qualification criteria |
| `customer.status_changed` | A customer's overall engagement status was updated |
| `customer.do_not_contact` | A customer was marked as do-not-contact |

---

### `CONVERSATION`
Events concerning individual conversations and messages within them.

| Event Type | Description |
|------------|-------------|
| `conversation.started` | A new conversation thread was initiated |
| `conversation.message_received` | An inbound message was received and stored |
| `conversation.message_sent` | An outbound message was sent to the customer |
| `conversation.ai_response_generated` | The AI engine completed generating a response |
| `conversation.intent_detected` | A significant intent was detected in a customer message |
| `conversation.completed` | A conversation reached a terminal state |
| `conversation.handoff_requested` | A conversation was flagged for human agent handoff |
| `conversation.error` | An error occurred during conversation processing |

---

### `MEETING`
Events concerning the meeting and appointment lifecycle.

| Event Type | Description |
|------------|-------------|
| `meeting.proposed` | A meeting time was suggested to a customer |
| `meeting.scheduled` | A meeting was confirmed and placed on a calendar |
| `meeting.rescheduled` | An existing meeting was moved to a new time |
| `meeting.cancelled` | A meeting was cancelled by any party |
| `meeting.reminder_sent` | A reminder notification was sent for an upcoming meeting |
| `meeting.occurred` | A meeting took place (as recorded by calendar integration) |
| `meeting.no_show` | A scheduled meeting occurred but the customer did not attend |
| `meeting.conflict_detected` | A scheduling conflict was identified |
| `meeting.conflict_resolved` | A previously detected conflict was resolved |

---

### `SCHEDULING`
Events concerning the Scheduling Engine's internal operations.

| Event Type | Description |
|------------|-------------|
| `scheduling.slot_evaluated` | A time slot was assessed for availability |
| `scheduling.calendar_synced` | Calendar availability was refreshed from an external source |
| `scheduling.availability_changed` | Agent or team availability windows were updated |
| `scheduling.booking_link_generated` | A self-booking link was created and sent |

---

### `FOLLOWUP`
Events concerning the Follow-up Intelligence Engine.

| Event Type | Description |
|------------|-------------|
| `followup.scheduled` | A follow-up action was placed in the execution queue |
| `followup.executed` | A follow-up message or action was sent |
| `followup.completed` | A follow-up sequence reached a successful terminal state |
| `followup.cancelled` | A follow-up was cancelled before execution |
| `followup.skipped` | A follow-up was skipped due to a policy rule |
| `followup.health_score_updated` | A customer's follow-up health score was recalculated |
| `followup.sequence_advanced` | A multi-step follow-up sequence advanced to the next step |

---

### `CRM`
Events concerning synchronization with CRM systems.

| Event Type | Description |
|------------|-------------|
| `crm.contact_synced` | A customer record was synchronized with an external CRM |
| `crm.deal_updated` | A deal or opportunity record was updated in an external CRM |
| `crm.sync_failed` | A synchronization attempt failed |
| `crm.field_mapped` | A HunterOS field was mapped to a CRM field |
| `crm.webhook_received` | An inbound webhook was received from an external CRM |

---

### `AUTOMATION`
Events concerning rule-based and AI-driven automated processes.

| Event Type | Description |
|------------|-------------|
| `automation.rule_triggered` | A defined automation rule matched and fired |
| `automation.rule_skipped` | An automation rule matched but was suppressed by policy |
| `automation.workflow_started` | A multi-step automation workflow began execution |
| `automation.workflow_completed` | A multi-step automation workflow finished |
| `automation.workflow_failed` | A multi-step automation workflow encountered a fatal error |

---

### `RESEARCH`
Events concerning the AI Research Agent (future phase).

| Event Type | Description |
|------------|-------------|
| `research.profile_requested` | Enrichment research was requested for a customer |
| `research.profile_completed` | Customer research was completed and stored |
| `research.source_retrieved` | A research data source was successfully queried |
| `research.insight_generated` | A research AI generated a significant insight |

---

### `PROPOSAL`
Events concerning the Proposal Generator (future phase).

| Event Type | Description |
|------------|-------------|
| `proposal.requested` | A proposal generation was initiated |
| `proposal.drafted` | An initial proposal draft was generated |
| `proposal.sent` | A proposal was delivered to the customer |
| `proposal.viewed` | A proposal was opened by the customer |
| `proposal.accepted` | A customer accepted a proposal |
| `proposal.rejected` | A customer declined a proposal |

---

### `ANALYTICS`
Events concerning analytical computations and insights.

| Event Type | Description |
|------------|-------------|
| `analytics.metric_computed` | A metric aggregation was completed |
| `analytics.report_generated` | A periodic or on-demand report was produced |
| `analytics.anomaly_detected` | An unusual pattern was identified in operational metrics |
| `analytics.forecast_updated` | A predictive forecast was recalculated |

---

### `AUDIT`
Events concerning platform-level audit and compliance operations.

| Event Type | Description |
|------------|-------------|
| `audit.access_granted` | A user or service was granted access to a resource |
| `audit.access_denied` | A user or service was denied access to a resource |
| `audit.configuration_changed` | Platform or workspace configuration was modified |
| `audit.data_exported` | Data was exported from the platform |
| `audit.data_deleted` | Data was removed from the platform |

---

### `NOTIFICATION`
Events concerning outbound notifications (distinct from customer messages).

| Event Type | Description |
|------------|-------------|
| `notification.sent` | An internal notification was dispatched |
| `notification.delivered` | A notification was confirmed delivered |
| `notification.failed` | A notification delivery attempt failed |
| `notification.preference_updated` | A user's notification preferences were changed |

---

### `AI_DECISION`
Events produced specifically by AI reasoning processes. These events always include the AI explainability fields defined in Section 6.5.

| Event Type | Description |
|------------|-------------|
| `ai_decision.intent_classified` | AI classified the intent of a customer message |
| `ai_decision.response_selected` | AI selected a communication strategy and generated a response |
| `ai_decision.followup_decision` | AI decided whether and how to follow up with a customer |
| `ai_decision.lead_scored` | AI assessed the qualification score of a lead |
| `ai_decision.anomaly_flagged` | AI flagged an unusual customer behavior pattern |
| `ai_decision.forecast_produced` | AI generated a predictive forecast |

---

### `PLATFORM`
Events concerning the HunterOS platform itself.

| Event Type | Description |
|------------|-------------|
| `platform.workspace_created` | A new workspace was provisioned |
| `platform.workspace_configured` | Workspace settings were updated |
| `platform.integration_connected` | An external integration was enabled |
| `platform.integration_disconnected` | An external integration was disabled |
| `platform.service_health_changed` | A platform service changed health status |

---

## 8. Event Publisher Contract

### 8.1 What Every Subsystem Is Allowed to Do

Every HunterOS subsystem, as a publisher, is entitled to:

- Construct event objects conforming to the Universal Event Model
- Call `event_bus.publish(event)` at any point during its operation
- Publish multiple events in the course of a single operation
- Include any relevant business data in the event payload

### 8.2 Publisher Obligations

Every publisher must:

**Publish at business action completion.** Events must be published after the business action has successfully completed, not before. A `MeetingScheduled` event must only be published after the meeting is durably stored.

**Populate all required fields.** event_id, occurred_at, workspace_id, source_subsystem, category, event_type, and schema_version are always required.

**Use past tense event names.** Event names describe what happened. They are never commands or present-tense descriptions.

**Keep payloads self-describing.** The payload should contain enough context for any consumer to understand the event without querying additional systems. Include identifiers for all referenced entities.

**Set correlation_id from the request context.** Every inbound request to HunterOS should carry or generate a correlation ID at its entry point. This ID must be propagated to every event published during that request's processing.

**Set causation_id when appropriate.** When an event is published as a direct result of consuming another event, the causation_id must reference the originating event's event_id.

### 8.3 What Publishers Must Never Do

Publishers must never:

- Import or call any consumer service directly as a reaction to their own business action
- Reference the Activity Timeline, Analytics Engine, Audit Trail, Dashboard, or Notification Service from within business logic
- Wait for consumer acknowledgment before returning to the caller
- Make publishing decisions based on which consumers they believe exist
- Include consumer-specific routing information in event payloads
- Publish events that describe intended future actions rather than completed past actions
- Modify or cancel a previously published event

### 8.4 Publisher Independence Test

Before merging any publisher code, apply this test:

> *"If every consumer were removed from the platform, would the publisher still function correctly?"*

If the answer is no — if the publisher's correctness depends on a consumer being present — the architecture has been violated.

---

## 9. Event Consumers

### 9.1 Consumer Responsibilities

A consumer is any component that registers interest in one or more event categories and takes action when matching events arrive. Consumers are fully autonomous. They do not coordinate with each other. They do not know which other consumers exist.

Every consumer must:

- Register its subscriptions at platform startup through the Event Bus's consumer registry
- Process events idempotently where possible — the same event may be delivered more than once in distributed scenarios
- Handle errors internally — consumer exceptions must be caught, logged, and must never propagate to the Event Bus
- Operate without side effects on publishers

### 9.2 The Standard Consumer Set

The following consumers are defined as part of the Phase 7 platform layer.

---

#### Activity Timeline Consumer

**Subscribes to:** All categories  
**Purpose:** Maintains a chronological, customer-scoped history of every significant business event.

The Activity Timeline Consumer receives events from across all domains and writes structured timeline entries to the Activity Timeline store. Each entry captures what happened, when it happened, who caused it, and what the context was.

This consumer is the sole mechanism by which the Activity Timeline is populated. No subsystem should write to the timeline directly.

See Section 11 for the architectural distinction between the Event Bus and the Activity Timeline.

---

#### Analytics Consumer

**Subscribes to:** `CONVERSATION`, `MEETING`, `FOLLOWUP`, `CUSTOMER`, `AI_DECISION`  
**Purpose:** Aggregates operational metrics and computes dashboard-facing statistics.

The Analytics Consumer processes events to maintain real-time and historical metric counters. It updates response time distributions, conversion rates, follow-up success rates, meeting show rates, and engagement scores.

No business subsystem should write analytics data directly. Analytics is exclusively a consumer of events.

---

#### Audit Trail Consumer

**Subscribes to:** All categories  
**Purpose:** Maintains a compliance-grade, immutable record of every platform action.

The Audit Trail Consumer writes events in their original form to the audit store. The audit trail is designed for regulatory compliance, enterprise customer audits, and internal security reviews. It preserves the full event including all AI decision fields.

The audit trail is append-only. No event may be modified or deleted from the audit trail.

---

#### Notification Consumer

**Subscribes to:** `MEETING`, `FOLLOWUP`, `CUSTOMER`, `CONVERSATION`, `PLATFORM`  
**Purpose:** Evaluates notification rules and dispatches alerts to human agents and operators.

The Notification Consumer applies workspace-level notification preferences against incoming events. When a matching rule fires, it dispatches the appropriate notification through the configured channels (email, in-app, webhook).

Notifications are themselves events. When a notification is dispatched, the Notification Consumer publishes a `notification.sent` event, which is itself stored in the Event Store.

---

#### Dashboard Consumer

**Subscribes to:** `CUSTOMER`, `CONVERSATION`, `MEETING`, `FOLLOWUP`, `AI_DECISION`  
**Purpose:** Updates the real-time operational dashboard with current platform state.

The Dashboard Consumer maintains the dashboard's live state by processing relevant events. No subsystem updates dashboard metrics directly. The dashboard's accuracy is a function of event completeness.

---

#### WebSocket Streaming Consumer

**Subscribes to:** All categories (filtered by workspace)  
**Purpose:** Pushes live event notifications to connected frontend clients.

The WebSocket Streaming Consumer maintains active WebSocket or Server-Sent Event connections to browser clients. When an event is published, the streaming consumer pushes a workspace-filtered notification to all connected clients for that workspace.

This enables real-time dashboard updates, live activity feeds, and instant notification delivery without polling.

---

#### Future AI Agent Consumers (Reserved)

**Subscribes to:** TBD per agent capability  
**Purpose:** Enable intelligent AI agents to observe platform events and act autonomously.

Future AI agent consumers — Research Agent, Proposal Agent, Voice Agent, Forecasting Agent — will register as consumers of relevant event categories. They observe events, apply intelligence, and publish their own events in response.

This is the integration pattern for all future AI capabilities. No existing code changes when a new AI agent is added.

---

### 9.3 Consumer Independence Principles

Each consumer must be deployable, testable, and operable independently of all other consumers. A consumer failure must not affect other consumers.

Consumers may read from the database to enrich their processing. They may not call other subsystem services directly as part of event handling. If a consumer needs to trigger a downstream action, it publishes an event.

---

## 10. Event Store

### 10.1 What the Event Store Is

The Event Store is the persistent, immutable log of every event ever published on the HunterOS Event Bus. It is not a state database. It does not store current state. It stores the complete history of every business action, in the exact sequence those actions occurred.

The Event Store is the source of truth for the platform's entire history.

### 10.2 Event Store Characteristics

**Immutability.** Events are written once. They are never updated. They are never deleted (except under legally mandated data erasure, which requires a special process outside the standard event lifecycle).

**Append-only.** New events are always added to the end of the log. Existing entries are never modified.

**Total ordering.** Events within a workspace are totally ordered by their sequence position in the store. This ordering is authoritative for all historical reconstruction.

**Completeness.** Every event that passes through the Event Bus is persisted before distribution to consumers. An event that was not stored did not happen.

### 10.3 What the Event Store Enables

**Complete History**

The Event Store contains the full operational history of every workspace, every customer, every conversation, and every AI decision. This history is queryable by any authorized system.

**Event Replay**

The Event Store can replay a slice of history to any consumer. This enables:
- Rebuilding a consumer's state after a failure
- Populating a new consumer with historical data on first deployment
- Debugging by replaying an exact sequence of events
- Testing consumers against production-identical event sequences

**Auditing**

Enterprise customers and compliance auditors may query the Event Store to answer: "What exactly happened during this engagement?" The answer is always complete and authoritative.

**Analytics Backfill**

If the Analytics Consumer fails and misses events, the Event Store allows those events to be replayed and the missing metrics recomputed. Analytics are never permanently lost because the source events are always available.

**AI Reasoning History**

Future AI agents may use the Event Store as a training signal or as contextual history when making decisions. A Forecasting Agent can read the complete sequence of customer interactions before making its prediction.

**Customer Timeline Reconstruction**

The Activity Timeline is not the only view of a customer's history. Any consumer can reconstruct a complete chronological view of all events related to a specific customer by querying the Event Store by customer_id.

**Enterprise Compliance**

Regulated industries require documented proof of what an AI system did and why. The Event Store, combined with AI decision fields, provides this proof for every decision the platform ever made.

### 10.4 The Event Store as a Strategic Asset

The Event Store accumulates value over time. On the first day of Phase 7, it contains one event. One year later, it contains millions. Those millions of events represent:

- A complete picture of which customer behaviors lead to closed deals
- A full history of which AI decisions were correct and which were not
- A training dataset for future AI model improvements
- A compliance record for auditors and regulators
- A source of competitive intelligence about the platform's own operational patterns

The Event Store is not a logging mechanism. It is a strategic business asset.

---

## 11. Activity Timeline

### 11.1 What the Activity Timeline Is

The Activity Timeline is a consumer of events. It is not the Event Bus. It is not the Event Store.

This distinction is critical and must be clearly understood by all engineers working on HunterOS.

```
Event Bus (infrastructure)
    │
    ▼
Event Store (immutable history)
    │
    ▼
Activity Timeline Consumer (one of many consumers)
    │
    ▼
Activity Timeline Store (read-optimized projection)
    │
    ▼
Timeline API Endpoint (serves UI)
    │
    ▼
Timeline UI Component (displays to users)
```

### 11.2 What the Timeline Does

The Activity Timeline Consumer subscribes to all event categories. When it receives an event, it writes a human-readable, customer-scoped timeline entry to a dedicated Timeline Store. This store is optimized for read operations — serving recent activity quickly for a specific customer.

The timeline is a **projection** of the Event Store, not the Event Store itself. It is a read-optimized view derived from events.

### 11.3 Why the Distinction Matters

If the Activity Timeline were also the Event Store, it would acquire responsibilities it is not designed for: replay, analytics, AI training, compliance auditing. The Timeline's purpose is to display recent activity in a human-readable format, not to serve as the system of record.

More importantly: if the Activity Timeline were the communication backbone rather than a consumer, then direct writes to the Timeline would appear throughout the codebase, recreating the tight coupling that Phase 7 is designed to eliminate.

The rule is absolute:

> **No subsystem may write directly to the Activity Timeline.** All timeline entries are produced exclusively by the Activity Timeline Consumer in response to events it receives from the Event Bus.

### 11.4 Timeline as Reconstruction

Because the Activity Timeline is derived from stored events, it can be rebuilt at any time. If the Timeline Store is lost, corrupted, or needs to be reformatted, the Event Store can replay all relevant events and the Timeline Consumer can reconstruct the complete history.

This is a material operational advantage. A direct-write timeline is a single point of failure. An event-derived timeline is reconstructible from the permanent record.

---

## 12. AI Explainability

### 12.1 The Enterprise Explainability Requirement

HunterOS makes hundreds or thousands of AI-driven decisions each day on behalf of enterprise customers. These decisions affect business relationships, communications to real humans, and revenue outcomes.

Enterprise customers — and increasingly, enterprise regulators — require the ability to audit AI decisions and understand:

- What decision was made
- What information the AI used to make it
- Why the AI chose this option over others
- How confident the AI was
- Which model version was responsible
- What the output of the decision was

Without explainability, HunterOS cannot be deployed in regulated industries. Without explainability, customers cannot trust that the AI is performing as intended. Without explainability, engineers cannot identify and correct AI regressions.

### 12.2 Explainability Through Events

Every AI-generated decision in HunterOS is published as an event of category `AI_DECISION`. These events populate the AI-specific fields defined in Section 6.5.

The explainability record for an AI decision consists of:

| Field | What It Records |
|-------|-----------------|
| `ai_model_version` | Exactly which model version made this decision, enabling version-specific auditing |
| `ai_reason` | A plain-language explanation of the decision rationale, written to be understood by a non-technical enterprise customer |
| `ai_confidence` | A normalized score (0.0 to 1.0) expressing how certain the model was. Low confidence decisions can be flagged for human review |
| `ai_evidence` | The specific signals, data points, or context fragments the model weighted in its decision |
| `ai_inputs` | The full structured input provided to the model — recreatable for debugging and comparison |
| `ai_outputs` | The full structured output from the model — including alternatives considered, not just the selected output |

### 12.3 Why This Is Non-Negotiable

**Enterprise sales** requires demonstrable AI governance. Procurement teams ask: "Can you show us exactly what your AI did and why?" Without event-level explainability, the answer is no.

**Error investigation** requires the ability to reconstruct what the AI saw and decided. Without ai_inputs and ai_outputs in the event record, debugging an incorrect AI decision requires log archaeology with no guarantee of success.

**Model version management** requires knowing exactly which model version made each decision. As models are updated, there must be a clear record of what changed and when.

**AI regression detection** requires comparing decision quality across model versions. The Event Store, filtered by ai_model_version, provides this dataset.

**Customer trust** requires transparency. When a customer asks "why did your AI say that to me?", HunterOS can provide a precise, sourced answer from the event record.

### 12.4 The Explainability Workflow

```
AI Engine makes a decision
       │
       ▼
AI constructs AI_DECISION event with:
  - reason (plain language)
  - confidence (0.0 - 1.0)
  - evidence (input signals)
  - inputs (full model input)
  - outputs (full model output, including alternatives)
  - model_version
       │
       ▼
Event published to Event Bus
       │
       ├──► Event Store (permanent record)
       │
       ├──► Audit Trail Consumer (compliance)
       │
       ├──► Analytics Consumer (model performance metrics)
       │
       └──► Activity Timeline Consumer (customer-facing history)
```

---

## 13. Live Event Streaming

### 13.1 The Problem with Polling

Traditional dashboard architectures poll for updates: the UI requests fresh data every N seconds. This approach has significant drawbacks:

- Dashboard state lags reality by up to N seconds
- N seconds of polling creates unnecessary database load
- Every connected user adds polling overhead
- Polling cannot deliver "instant" updates for time-sensitive operations

### 13.2 Event-Driven Live Updates

In the Phase 7 architecture, the Event Bus provides the solution. The WebSocket Streaming Consumer subscribes to all events on the Event Bus and maintains persistent connections to browser clients. When an event is published, it is pushed to connected clients within milliseconds.

The frontend receives a stream of events from which it can update its display without polling. The backend emits events once; all connected clients receive them simultaneously.

### 13.3 Connection Architecture

```
Event Bus
    │
    ▼
WebSocket Streaming Consumer
    │
    ├──► Filters events by workspace
    │
    ├──► Serializes event to wire format
    │
    └──► Broadcasts to all active connections for workspace
              │
              ├──► Client 1 (Agent Dashboard)
              ├──► Client 2 (Analytics View)
              └──► Client N (Admin Console)
```

### 13.4 Implementation Considerations

The streaming consumer must handle:

**Connection lifecycle.** Clients connect and disconnect at any time. The streaming consumer maintains a connection registry and removes stale connections without error.

**Workspace scoping.** Events must only be delivered to clients authenticated for the event's workspace. No event from workspace A may reach a client authenticated for workspace B.

**Event serialization.** Events are serialized to a wire format (JSON) that excludes sensitive fields not appropriate for frontend consumption.

**Backpressure.** If a client cannot consume events fast enough, the streaming consumer must implement appropriate backpressure to prevent resource exhaustion.

**Reconnection.** When a client reconnects after a disconnection, the streaming consumer provides a mechanism to receive events published during the disconnection window (using Event Store replay).

### 13.5 Technology Options

The streaming consumer may be implemented using:

- **WebSockets** — bidirectional, suitable for highly interactive dashboards that also send commands
- **Server-Sent Events (SSE)** — unidirectional, simpler to implement, sufficient for read-only live feeds

The choice of streaming technology is an implementation detail, not an architectural decision. The Event Bus emits the same events regardless of which technology the streaming consumer uses.

---

## 14. Extensibility

### 14.1 The Extension Pattern

Phase 7's Event-Driven Architecture is designed so that every future capability integrates through the same pattern:

> Publish events for what you produce. Subscribe to events for what you need.

No future phase should require modifications to existing publishers. Every new capability is additive, not intrusive.

### 14.2 Future Phase Integration Examples

---

#### Research Agent (Future Phase)

The Research Agent enriches customer profiles by gathering external intelligence.

**As a consumer:** Subscribes to `customer.created` and `customer.status_changed` events to trigger research when new leads enter the system.

**As a publisher:** Publishes `research.profile_completed` and `research.insight_generated` events when enrichment is complete.

**No existing code changes.** The Conversation Engine, Scheduling Engine, and Follow-up Engine continue operating identically. The Research Agent plugs in by registering its subscriptions.

---

#### Proposal Generator (Future Phase)

The Proposal Generator creates tailored proposals based on conversation intelligence.

**As a consumer:** Subscribes to `ai_decision.intent_classified` events where intent is `intent.ready_for_proposal`, and `meeting.occurred` events as triggers.

**As a publisher:** Publishes `proposal.drafted`, `proposal.sent`, `proposal.viewed`, `proposal.accepted`, and `proposal.rejected` events.

**No existing code changes.**

---

#### Voice Agent (Future Phase)

The Voice Agent handles inbound and outbound calls.

**As a consumer:** Subscribes to `meeting.scheduled` events to prepare for upcoming calls, and `customer.status_changed` events to determine call priorities.

**As a publisher:** Publishes `conversation.message_received` and `conversation.message_sent` events with `channel: voice`, and `ai_decision.*` events for all AI reasoning performed during calls.

**No existing code changes.** The same consumers that process WhatsApp conversation events will automatically process voice conversation events because they subscribe to the same event categories.

---

#### Revenue Forecasting (Future Phase)

The Forecasting Engine predicts pipeline value and deal velocity.

**As a consumer:** Subscribes to `meeting.*`, `proposal.*`, `customer.*`, and `ai_decision.lead_scored` events to maintain its predictive model inputs.

**As a publisher:** Publishes `analytics.forecast_updated` events when predictions are refreshed.

**No existing code changes.**

---

#### Executive Reporting (Future Phase)

The Executive Reporting Engine generates periodic intelligence summaries.

**As a consumer:** Subscribes to `analytics.metric_computed`, `analytics.forecast_updated`, and `analytics.anomaly_detected` events.

**As a publisher:** Publishes `analytics.report_generated` events when reports are ready.

**No existing code changes.**

---

#### Pipeline Intelligence (Future Phase)

The Pipeline Intelligence module provides deal stage prediction and bottleneck analysis.

**As a consumer:** Subscribes to `customer.*`, `conversation.*`, `meeting.*`, `proposal.*`, and `followup.*` events to maintain deal stage models.

**As a publisher:** Publishes `ai_decision.lead_scored` and `analytics.anomaly_detected` events when significant patterns are identified.

**No existing code changes.**

---

### 14.3 The Extensibility Test

Before any future phase begins implementation, apply this test:

> *"Does this phase require modifying an existing publisher to add a new consumer?"*

If yes, the design is wrong. Revisit the event taxonomy. Add missing events if necessary. Do not modify existing publishers for the benefit of new consumers.

---

## 15. Folder Structure

The Event Infrastructure is its own independent domain within HunterOS. It must not reside inside any existing business domain directory. It must not be co-located with conversations, scheduling, follow-up, or any other business capability.

The following structure defines the canonical layout for Phase 7:

```
app/
│
├── events/                          # Platform-level Event Infrastructure
│   │                                # (exists as of Phase 7)
│   ├── __init__.py
│   │
│   ├── bus/                         # Core Event Bus infrastructure
│   │   ├── __init__.py
│   │   ├── event_bus.py             # Bus interface and dispatch logic
│   │   ├── registry.py              # Consumer registration and management
│   │   └── exceptions.py            # Bus-specific error types
│   │
│   ├── model/                       # Universal Event Model
│   │   ├── __init__.py
│   │   ├── base_event.py            # Universal Event base definition
│   │   ├── categories.py            # Event category enumeration
│   │   └── actor_types.py           # Actor type enumeration
│   │
│   ├── store/                       # Immutable Event Store
│   │   ├── __init__.py
│   │   ├── event_store.py           # Store interface and append logic
│   │   ├── query.py                 # Event Store query and replay logic
│   │   └── models.py                # Persistence models for stored events
│   │
│   ├── categories/                  # Event definitions by category
│   │   ├── __init__.py
│   │   ├── customer_events.py       # CUSTOMER category event definitions
│   │   ├── conversation_events.py   # CONVERSATION category event definitions
│   │   ├── meeting_events.py        # MEETING category event definitions
│   │   ├── scheduling_events.py     # SCHEDULING category event definitions
│   │   ├── followup_events.py       # FOLLOWUP category event definitions
│   │   ├── crm_events.py            # CRM category event definitions
│   │   ├── automation_events.py     # AUTOMATION category event definitions
│   │   ├── research_events.py       # RESEARCH category event definitions
│   │   ├── proposal_events.py       # PROPOSAL category event definitions
│   │   ├── analytics_events.py      # ANALYTICS category event definitions
│   │   ├── audit_events.py          # AUDIT category event definitions
│   │   ├── notification_events.py   # NOTIFICATION category event definitions
│   │   ├── ai_decision_events.py    # AI_DECISION category event definitions
│   │   └── platform_events.py       # PLATFORM category event definitions
│   │
│   └── streaming/                   # Live event streaming infrastructure
│       ├── __init__.py
│       ├── stream_manager.py        # WebSocket / SSE connection management
│       └── serializer.py            # Event serialization for wire transport
│
├── consumers/                       # Platform-level consumer implementations
│   ├── __init__.py
│   ├── registry.py                  # Consumer registration at startup
│   │
│   ├── timeline/                    # Activity Timeline Consumer
│   │   ├── __init__.py
│   │   ├── consumer.py              # Event subscription and routing
│   │   └── writer.py                # Timeline entry construction and storage
│   │
│   ├── analytics/                   # Analytics Consumer
│   │   ├── __init__.py
│   │   ├── consumer.py
│   │   └── aggregator.py
│   │
│   ├── audit/                       # Audit Trail Consumer
│   │   ├── __init__.py
│   │   └── consumer.py
│   │
│   ├── notifications/               # Notification Consumer
│   │   ├── __init__.py
│   │   ├── consumer.py
│   │   └── rule_engine.py
│   │
│   ├── dashboard/                   # Dashboard Consumer
│   │   ├── __init__.py
│   │   └── consumer.py
│   │
│   └── streaming/                   # WebSocket Streaming Consumer
│       ├── __init__.py
│       └── consumer.py
│
├── domain/                          # Business domains (publishers)
│   ├── conversations/               # Publishes CONVERSATION events
│   ├── scheduling/                  # Publishes MEETING, SCHEDULING events
│   ├── followup/                    # Publishes FOLLOWUP events
│   ├── customers/                   # Publishes CUSTOMER events
│   ├── leads/                       # Publishes CUSTOMER, AUDIT events
│   └── ...
│
└── ...
```

### 15.1 Critical Structural Rules

**The `events/` directory is platform infrastructure.** It must not import from any domain under `domain/`. Domain code may import from `events/` to publish events, never the reverse.

**The `consumers/` directory is platform infrastructure.** Consumer implementations may import from `events/` and from `domain/` models for database access. Consumers must not call domain services.

**Each domain directory contains only its own logic.** A domain may import event definitions from `events/categories/` to construct events. It must not import from other domain directories as a reaction mechanism.

**The `bus/` directory has zero business domain imports.** The Event Bus itself is pure infrastructure. It knows nothing about conversations, meetings, or follow-ups.

---

## 16. Deliverables

Phase 7 must produce the following artifacts. Each deliverable builds upon the last and must be functional and tested before the next is begun.

---

### Deliverable 1 — Universal Event Model

**What:** The platform-level base event class implementing the Universal Event Model defined in Section 6.

**Includes:**
- Base event structure with all Identity, Context, Content, and AI Decision fields
- Category enumeration covering all standard categories defined in Section 7
- Actor type enumeration
- Schema validation

**Success signal:** Any subsystem can construct a valid event of any category using the base model.

---

### Deliverable 2 — Event Category Definitions

**What:** Concrete event classes for all event types defined in Section 7, organized by category.

**Includes:**
- One file per event category under `app/events/categories/`
- All event types listed in Section 7
- Docstrings explaining when each event should be published

**Success signal:** Every business action in HunterOS has a corresponding event definition it can use.

---

### Deliverable 3 — Enhanced Event Bus

**What:** An upgraded Event Bus that replaces the existing synchronous dispatcher with a fully capable platform-level bus.

**Includes:**
- Consumer registration mechanism
- Event Store write before consumer delivery
- Isolated consumer error handling
- Structured logging for every dispatch operation
- Clear upgrade path to async/distributed delivery (Redis Streams, Celery)

**Success signal:** Events are persisted before distribution. Consumer failures are logged and do not affect other consumers or publishers.

---

### Deliverable 4 — Immutable Event Store

**What:** The persistence layer for all platform events.

**Includes:**
- Append-only write operation
- Event retrieval by event_id, workspace_id, customer_id, conversation_id, category, and time range
- Replay capability (retrieve all events for a given consumer from a given position)
- Database migration for the event store table

**Success signal:** All events published to the Event Bus are durably stored. Events can be queried and replayed from any position.

---

### Deliverable 5 — Platform Consumer Registry

**What:** The mechanism by which all consumers register their subscriptions at platform startup.

**Includes:**
- A single registration function called during application startup
- Registration of all standard consumers defined in Section 9.2
- Verification that all consumer registrations are valid at startup

**Success signal:** All consumers are registered before the first request is served.

---

### Deliverable 6 — Standard Consumers

**What:** Implementations of all platform-level consumers defined in Section 9.2.

**Includes:**
- Activity Timeline Consumer
- Analytics Consumer
- Audit Trail Consumer
- Notification Consumer
- Dashboard Consumer
- WebSocket Streaming Consumer

**Success signal:** Each consumer processes relevant events independently. A failure in one consumer does not affect others.

---

### Deliverable 7 — Publisher Migration

**What:** Migration of all existing subsystem publishers to use the new Event Bus and Universal Event Model.

**Includes:**
- Conversion of existing `message_events.py` definitions to Universal Event Model format
- Migration of all direct service calls in publishers to event publications
- Removal of all direct consumer references from publisher code

**Success signal:** No publisher imports or directly calls any consumer service.

---

### Deliverable 8 — Live Event Streaming

**What:** WebSocket or SSE infrastructure for live event delivery to browser clients.

**Includes:**
- Connection manager with workspace-scoped session tracking
- Event serialization for wire transport
- Frontend event reception integration point

**Success signal:** Events published on the backend appear in connected browser clients within one second of publication.

---

### Deliverable 9 — Architecture Verification

**What:** Automated checks that verify the architectural constraints of Phase 7 are not violated.

**Includes:**
- Import boundary verification (domains do not import from other domains)
- Publisher contract verification (no publisher calls consumer services)
- Event model validation (all required fields are present)

**Success signal:** All architectural constraints are enforceable through automated checks.

---

## 17. Success Criteria

Phase 7 is architecturally complete when every criterion below is satisfied.

---

### Communication Architecture

```
✔  No subsystem directly calls the Analytics Engine as a reaction to its own actions
✔  No subsystem directly calls the Dashboard as a reaction to its own actions
✔  No subsystem directly calls the Audit Trail as a reaction to its own actions
✔  No subsystem directly calls the Notification Service as a reaction to its own actions
✔  No subsystem directly calls the Activity Timeline as a reaction to its own actions
✔  All cross-subsystem reactions are mediated exclusively through the Event Bus
```

---

### Publisher Compliance

```
✔  Every significant business action in HunterOS publishes a corresponding event
✔  All events conform to the Universal Event Model defined in Section 6
✔  All published events use category and event_type values defined in Section 7
✔  All publishers use past-tense event names
✔  No publisher references its consumers in its import graph
```

---

### Consumer Independence

```
✔  Each consumer can be deployed, tested, and operated independently
✔  A consumer failure produces a logged error and does not interrupt other consumers
✔  Adding a new consumer requires zero modifications to any publisher
✔  Each consumer has a documented subscription declaration
```

---

### Event Store Integrity

```
✔  Every event published to the Event Bus is durably persisted before consumer delivery
✔  The Event Store is append-only — no updates or deletes in the normal event path
✔  Events can be retrieved by event_id, workspace_id, customer_id, conversation_id, and time range
✔  The Event Store can replay events to any consumer from any position
```

---

### Activity Timeline

```
✔  The Activity Timeline is populated exclusively by the Timeline Consumer
✔  No business subsystem writes directly to the Activity Timeline
✔  The Activity Timeline can be fully reconstructed from Event Store replay
✔  Timeline entries are visible in the frontend within seconds of the originating event
```

---

### AI Explainability

```
✔  Every AI decision is published as an AI_DECISION category event
✔  Every AI_DECISION event includes reason, confidence, evidence, inputs, outputs, and model_version
✔  AI decision history is queryable from the Event Store by workspace and time range
✔  AI decision events are stored in the Audit Trail
```

---

### Live Streaming

```
✔  Events published on the backend appear in connected browser clients within one second
✔  Live events are scoped to the authenticated workspace — no cross-workspace leakage
✔  Client disconnections and reconnections are handled gracefully
```

---

### Extensibility

```
✔  A new consumer can be added and integrated without modifying any existing publisher
✔  A new event type can be added to the taxonomy without modifying existing consumers
✔  The architecture documentation serves as the sole specification for future phases
✔  Future AI agents can integrate exclusively through event publication and subscription
```

---

## Appendix A — Architectural Governance

### A.1 How to Evaluate Future Changes Against This Architecture

Before implementing any feature in a future phase, apply the following evaluation:

1. **Identify all new business actions.** Every significant action must have a corresponding event.

2. **Identify all cross-subsystem reactions.** If subsystem A must react to subsystem B's action, that reaction must be implemented as a consumer of the event B publishes — not as a direct call.

3. **Identify all new data consumers.** If a new capability needs to receive data from an existing subsystem, it subscribes to the appropriate events. It does not call the subsystem directly.

4. **Check the import graph.** Before merging, verify that no publisher imports from a consumer, and no domain imports from a sibling domain for reactive purposes.

5. **Verify the event model.** All new events must use the Universal Event Model. All required fields must be populated.

### A.2 When to Add New Event Categories

A new event category should be added when a future phase introduces a capability that is materially distinct from all existing categories, and multiple event types within that capability are expected.

New categories are added to the taxonomy in Section 7 of this document and to the category enumeration in `app/events/model/categories.py`. All existing consumers and publishers continue operating unchanged.

### A.3 When to Modify Existing Events

Event schemas should be treated as contracts. Existing events should not have fields removed or renamed. New fields may be added with default values. Breaking changes require a schema version increment and a consumer migration plan.

---

## Appendix B — Glossary

| Term | Definition |
|------|------------|
| **Event** | An immutable record of a business action that has occurred. Always past tense. |
| **Event Bus** | The platform-level communication backbone that receives events from publishers and distributes them to consumers. |
| **Event Store** | The immutable, append-only persistence layer for all events that pass through the Event Bus. |
| **Publisher** | Any subsystem that constructs and publishes events to the Event Bus. |
| **Consumer** | Any component that registers interest in events and processes them when received. |
| **Activity Timeline** | A read-optimized, customer-scoped projection of selected events. One consumer among many. |
| **Correlation ID** | A shared identifier linking all events produced by a single end-to-end operation. |
| **Causation ID** | The event_id of the event that directly caused a subsequent event to be published. |
| **Payload** | The domain-specific data carried by an event. Varies by event type. |
| **Schema Version** | An integer tracking the structural version of an event definition. Incremented on breaking changes. |
| **Actor** | The agent (human, AI, or system) responsible for the business action that produced an event. |
| **AI Explainability** | The practice of recording AI reasoning, evidence, confidence, and decision context in AI_DECISION events. |
| **Replay** | The process of re-delivering stored events from the Event Store to a consumer, starting from a specified position. |
| **Projection** | A read-optimized data structure derived from events in the Event Store. The Activity Timeline is a projection. |
| **Consumer Independence** | The principle that each consumer operates, fails, and recovers without affecting any other consumer. |

---

*End of HunterOS Phase 7 Architecture Specification*

*This document is the architectural constitution for all future HunterOS engineering phases.*  
*All future phases must comply with the principles and patterns defined herein.*  
*Deviations require explicit architectural review and amendment to this document.*

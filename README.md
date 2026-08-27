# FM Genie

## Autonomous AI Facilities Management Agent

FM Genie is an autonomous Facilities Management (FM) agent that converts natural-language workplace issues into governed, trackable service workflows.

Instead of requiring users to manually select categories, priorities, teams, SLAs, and ticket states, FM Genie understands the request and orchestrates the appropriate FM workflow.

---

## Key Capabilities

### 1. Natural-Language Ticket Creation

Users can simply describe an issue.

Example:

> The air conditioner is not cooling in Meeting Room B on the 3rd floor.

FM Genie identifies:

- Category: HVAC
- Priority: Medium
- SLA: 8 hours
- Responsible Team: HVAC Services
- Location: Meeting Room B, 3rd floor

and creates a Firestore-backed ticket.

---

### 2. Safety-Critical Issue Detection

FM Genie recognizes safety-critical situations such as:

- Fire
- Smoke
- Sparks
- Exposed electrical wires
- Electric shock
- Structural collapse
- Falling ceiling
- Major building damage
- Immediate danger to employees

Safety-critical requests receive a safety override.

Example:

> There are sparks from an exposed electrical wire and an employee has received an electric shock.

The system can create a ticket with:

- Priority: Critical
- SLA: Immediate
- Safety-critical: True
- Emergency responsible team
- Safety escalation notification

The agent also provides an appropriate safety warning.

---

### 3. Complete Ticket Lifecycle

FM Genie supports the ticket lifecycle:

OPEN
→ ASSIGNED
→ IN_PROGRESS
→ PENDING_VENDOR
→ RESOLVED
→ CLOSED

It also supports:

RESOLVED
→ REOPENED

when the issue returns within the configured reopening window.

The reopening policy currently uses a 2-working-day window.

---

### 4. Requester Notifications

When a ticket is resolved, FM Genie creates a requester notification.

Safety-critical incidents can also generate safety escalation notifications.

Notifications are stored in Firestore and can be retrieved using the ticket ID.

---

### 5. SLA Monitoring

FM Genie monitors:

- Safety-critical tickets
- SLA breaches
- Approaching SLA deadlines
- On-track tickets
- Tickets without SLA

The SLA logic is implemented separately from the conversational agent so that operational rules remain deterministic.

---

### 6. FM Admin Dashboard

Administrators can ask:

> Give me the current FM Admin dashboard including team workload.

FM Genie retrieves current Firestore data and reports:

- Total tickets
- Active tickets
- Status counts
- SLA summary
- Safety-critical tickets
- SLA breaches
- Approaching SLA
- On-track tickets
- Tickets without SLA
- Category-wise ticket counts
- Responsible-team workload

---

# Architecture

```text
                    +----------------------+
                    |     User / Admin     |
                    | Natural-language FM  |
                    |       request        |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |      FM Genie        |
                    | Google ADK + Gemini  |
                    +----------+-----------+
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
   +-------------+      +-------------+      +-------------+
   | Ticket      |      | SLA / Safety|      |Notification |
   | Lifecycle   |      | Rules       |      | Engine      |
   +------+------+      +------+------+      +------+------+
          |                    |                    |
          +--------------------+--------------------+
                               |
                               v
                    +----------------------+
                    |      Firestore       |
                    |                      |
                    | tickets              |
                    | ticket_events        |
                    | notifications        |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |    FM Admin KPIs     |
                    | Status / SLA / Safety|
                    | Category / Workload  |
                    +----------------------+
```

---

# Project Structure

```text
fm-genie/
|
+-- fm_genie/
|   +-- agent.py
|
|   +-- rules/
|   |   +-- safety_rules.py
|   |   +-- sla_matrix.py
|
|   +-- tools/
|       +-- ticket_tools.py
|       +-- notification_tools.py
|       +-- sla_tools.py
|       +-- dashboard_tools.py
|
+-- test_safety.py
+-- backups/
|   +-- final_working/
|
+-- README.md
```

---

# Agent Tools

FM Genie currently exposes eight tools:

1. `create_ticket`
2. `get_ticket_status`
3. `update_ticket_status`
4. `reopen_ticket`
5. `create_notification`
6. `get_ticket_notifications`
7. `check_sla_status`
8. `get_fm_dashboard`

---

# Ticket Lifecycle Example

```text
User reports issue
       |
       v
FM Genie understands request
       |
       v
Category / Priority / SLA / Team
       |
       v
Ticket created in Firestore
       |
       v
OPEN
       |
       v
IN_PROGRESS
       |
       v
RESOLVED
       |
       v
Requester notification
       |
       v
Issue returns?
       |
       v
REOPENED
```

---

# Safety Workflow

```text
Natural-language request
          |
          v
Safety indicators detected
          |
          v
Safety override
          |
          v
Critical priority
          |
          v
Immediate SLA
          |
          v
Emergency responsible team
          |
          v
Safety escalation notification
          |
          v
Safety advisory to users
```

---

# Data Model

## tickets

Ticket records contain operational information such as:

- ticket_id
- issue_description
- category
- priority
- status
- SLA
- SLA due time
- requester
- location
- responsible team
- safety-critical status
- safety trigger
- escalation status
- created_at
- updated_at
- resolved_at
- closed_at

## ticket_events

Lifecycle events are recorded for auditability.

Examples:

- CREATED
- STATUS_CHANGED
- REQUESTER_NOTIFIED

## notifications

Notification records contain:

- Notification ID
- Ticket ID
- Recipient
- Notification type
- Message
- Status
- Creation timestamp

---

# Example User Interactions

### Normal FM Request

**User**

> The washroom tap is leaking on the 3rd floor near the cafeteria.

FM Genie identifies the issue as a Plumbing request and creates a trackable FM ticket.

### Safety Emergency

**User**

> There are sparks from an exposed electrical wire and an employee has received an electric shock on the 4th floor.

FM Genie identifies the request as safety-critical and creates an emergency ticket with Critical priority and Immediate response requirements.

### Ticket Status

**User**

> What's the status of FM-8JCKDNFC?

FM Genie retrieves the current status directly from Firestore.

### Reopening

**User**

> The HVAC issue has come back. Please reopen ticket FM-8JCKDNFC.

FM Genie invokes the reopening workflow and enforces the 2-working-day reopening rule.

### Admin Dashboard

**User**

> Give me the current FM Admin dashboard including team workload.

FM Genie retrieves current operational KPIs from Firestore.

---

# Design Principles

### Tool-backed actions

The agent does not invent ticket IDs, statuses, SLA information, notifications or operational actions.

### Deterministic operational rules

Safety and SLA decisions are implemented through dedicated rule and tool logic rather than relying entirely on conversational reasoning.

### Firestore as the operational source of truth

Ticket and notification state is persisted in Firestore.

### Auditable lifecycle

Important ticket transitions are recorded as ticket events.

### Safety-first behavior

Safety-critical requests receive immediate attention and explicit safety guidance.

---

# Current Validation

The implementation has been tested for:

- Ticket creation
- Ticket status retrieval
- Status updates
- Resolution
- Duplicate resolution protection
- Requester resolution notifications
- Ticket reopening
- 2-working-day reopening validation
- Safety-critical detection
- Safety escalation notifications
- SLA monitoring
- SLA breach detection
- Admin dashboard generation
- Team workload reporting
- Firestore persistence
- Eight-tool agent registration

---

# Running FM Genie

```bash
adk run fm_genie
```

The agent can then be tested using natural-language requests.

---

# Safety Notice

FM Genie provides software-based workflow orchestration and safety guidance.

It does not claim that emergency personnel have physically arrived or that an incident has been physically dispatched unless a connected operational system explicitly confirms that action.

For real emergencies, users should follow their organization's emergency procedures and contact the appropriate emergency services.

---

# Project Status

FM Genie currently provides a working prototype of an autonomous Facilities Management workflow agent with:

- Natural-language ticket creation
- Automatic categorization
- Priority determination
- SLA assignment
- Responsible-team assignment
- Safety-critical escalation
- Ticket status management
- Ticket reopening
- Requester notifications
- SLA monitoring
- Admin KPI dashboard
- Team workload reporting
- Firestore persistence
- Ticket event auditing

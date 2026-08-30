from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from ..rules.safety_rules import detect_safety_risk
from ..rules.sla_matrix import get_sla
from .notification_tools import create_notification


db = firestore.Client()


def _log_ticket_event(
    ticket_id: str,
    event_type: str,
    message: str,
    status: str,
    actor: str = "FM Genie",
) -> None:
    """Write an immutable lifecycle event for a ticket."""

    now = datetime.now(timezone.utc)

    event = {
        "ticket_id": ticket_id,
        "event_type": event_type,
        "message": message,
        "status": status,
        "actor": actor,
        "created_at": now,
    }

    db.collection("ticket_events").add(event)


def _sla_to_timedelta(sla: str):
    """Convert a prototype SLA string into a timedelta."""

    value = sla.strip().lower()

    if value == "immediate":
        return timedelta(seconds=0)

    if "minute" in value:
        minutes = int(value.split()[0])
        return timedelta(minutes=minutes)

    if "hour" in value:
        hours = int(value.split()[0])
        return timedelta(hours=hours)

    if "working day" in value:
        days = int(value.split()[0])
        return timedelta(hours=8 * days)

    return None


def _create_safety_notification(
    ticket_id: str,
    responsible_team: str,
    location: str,
    issue_description: str,
) -> dict:
    """Create a safety escalation notification for a critical ticket."""

    message = (
        f"Emergency safety incident reported at {location or 'the workplace'}. "
        f"Immediate response required. "
        f"Issue: {issue_description}"
    )

    notification = create_notification(
        ticket_id=ticket_id,
        recipient=responsible_team,
        notification_type="SAFETY_ESCALATION",
        message=message,
    )

    return notification


def _create_resolution_notification(
    ticket_id: str,
    requester: str,
    responsible_team: str,
) -> dict:
    """Create a requester notification when a ticket is resolved."""

    message = (
        f"Ticket {ticket_id} has been resolved"
        f"{' by ' + responsible_team if responsible_team else ''}."
    )

    return create_notification(
        ticket_id=ticket_id,
        recipient=requester,
        notification_type="RESOLUTION",
        message=message,
    )


def _resolution_notification_exists(ticket_id: str) -> bool:
    """Return True when a resolution notification already exists."""

    documents = (
        db.collection("notifications")
        .where(
            filter=firestore.FieldFilter(
                "ticket_id",
                "==",
                ticket_id,
            )
        )
        .where(
            filter=firestore.FieldFilter(
                "notification_type",
                "==",
                "RESOLUTION",
            )
        )
        .limit(1)
        .stream()
    )

    return any(True for _ in documents)


def create_ticket(
    issue_description: str,
    category: str,
    priority: str,
    sla: str = "",
    responsible_team: str = "",
    location: str = "",
    requester: str = "Demo User",
) -> dict:
    """Create a new FM service ticket in Firestore."""

    category = category.strip()
    priority = priority.strip().title()

    # ---------------------------------------------------------
    # SAFETY OVERRIDE
    # ---------------------------------------------------------
    safety = detect_safety_risk(issue_description)

    if safety["is_safety_critical"]:
        priority = "Critical"
        sla = safety["response"]
        responsible_team = safety["escalation"]

    else:
        # -----------------------------------------------------
        # DETERMINISTIC SLA RULE
        # -----------------------------------------------------
        sla_rule = get_sla(category, priority)
        sla = sla_rule["resolution"]

        # -----------------------------------------------------
        # DETERMINISTIC TEAM ROUTING
        # -----------------------------------------------------
        team_by_category = {
            "HVAC": "HVAC Services",
            "Plumbing": "Plumbing Services",
            "Cafeteria": "Cafeteria Services",
            "Electrical": "Electrical Services",
            "Housekeeping": "Housekeeping Services",
            "Furniture": "Carpentry Services",
        }

        if not responsible_team:
            responsible_team = team_by_category.get(
                category,
                "",
            )

    now = datetime.now(timezone.utc)

    sla_duration = _sla_to_timedelta(sla)

    if sla_duration is not None:
        sla_due_at = now + sla_duration
    else:
        sla_due_at = None

    if safety["is_safety_critical"]:
        escalation_status = "IMMEDIATE"
    else:
        escalation_status = "NOT_ESCALATED"

    # ---------------------------------------------------------
    # CREATE TICKET
    # ---------------------------------------------------------
    ticket_ref = db.collection("tickets").document()

    ticket_id = f"FM-{ticket_ref.id[:8].upper()}"

    ticket = {
        "ticket_id": ticket_id,
        "requester": requester,
        "issue_description": issue_description,
        "category": category,
        "priority": priority,
        "sla": sla,
        "sla_due_at": sla_due_at,
        "responsible_team": responsible_team,
        "location": location,
        "status": "OPEN",
        "safety_critical": safety["is_safety_critical"],
        "safety_trigger": safety["trigger"],
        "escalation": safety["escalation"],
        "escalation_status": escalation_status,
        "created_at": now,
        "updated_at": now,
    }

    ticket_ref.set(ticket)

    # ---------------------------------------------------------
    # LOG CREATION EVENT
    # ---------------------------------------------------------
    _log_ticket_event(
        ticket_id=ticket_id,
        event_type="CREATED",
        message=f"Ticket {ticket_id} was created.",
        status="OPEN",
    )

    # ---------------------------------------------------------
    # AUTOMATIC SAFETY ESCALATION NOTIFICATION
    # ---------------------------------------------------------
    safety_notification = None

    if safety["is_safety_critical"]:
        safety_notification = _create_safety_notification(
            ticket_id=ticket_id,
            responsible_team=responsible_team,
            location=location,
            issue_description=issue_description,
        )

        if safety_notification.get("success"):
            _log_ticket_event(
                ticket_id=ticket_id,
                event_type="SAFETY_NOTIFICATION_CREATED",
                message=(
                    f"Safety escalation notification created for "
                    f"{responsible_team}."
                ),
                status="OPEN",
                actor="FM Genie",
            )

    return {
        "success": True,
        "ticket_id": ticket_id,
        "status": "OPEN",
        "category": category,
        "priority": priority,
        "sla": sla,
        "sla_due_at": (
            sla_due_at.isoformat()
            if sla_due_at
            else None
        ),
        "responsible_team": responsible_team,
        "location": location,
        "safety_critical": safety["is_safety_critical"],
        "safety_trigger": safety["trigger"],
        "escalation": safety["escalation"],
        "escalation_status": escalation_status,
        "safety_notification_created": (
            safety_notification.get("success")
            if safety_notification
            else False
        ),
        "message": (
            f"FM ticket {ticket_id} has been created successfully."
        ),
    }


def get_ticket_status(ticket_id: str) -> dict:
    """Retrieve the current status and details of an FM ticket."""

    normalized_id = ticket_id.strip().upper()

    query = (
        db.collection("tickets")
        .where(
            filter=firestore.FieldFilter(
                "ticket_id",
                "==",
                normalized_id,
            )
        )
        .limit(1)
        .stream()
    )

    documents = list(query)

    if not documents:
        return {
            "success": False,
            "message": (
                f"Ticket {normalized_id} was not found."
            ),
        }

    ticket = documents[0].to_dict()

    return {
        "success": True,
        "ticket_id": ticket.get("ticket_id"),
        "status": ticket.get("status"),
        "category": ticket.get("category"),
        "priority": ticket.get("priority"),
        "sla": ticket.get("sla"),
        "sla_due_at": (
            ticket.get("sla_due_at").isoformat()
            if ticket.get("sla_due_at")
            else None
        ),
        "location": ticket.get("location"),
        "responsible_team": ticket.get(
            "responsible_team"
        ),
        "issue_description": ticket.get(
            "issue_description"
        ),
        "safety_critical": ticket.get(
            "safety_critical",
            False,
        ),
        "safety_trigger": ticket.get(
            "safety_trigger",
            "",
        ),
        "escalation": ticket.get(
            "escalation",
            "",
        ),
        "escalation_status": ticket.get(
            "escalation_status",
            "NOT_ESCALATED",
        ),
        "resolved_at": (
            ticket.get("resolved_at").isoformat()
            if ticket.get("resolved_at")
            else None
        ),
        "closed_at": (
            ticket.get("closed_at").isoformat()
            if ticket.get("closed_at")
            else None
        ),
        "message": (
            f"Ticket {normalized_id} is currently "
            f"{ticket.get('status')}."
        ),
    }


def update_ticket_status(
    ticket_id: str,
    new_status: str,
    responsible_team: str = "",
) -> dict:
    """Update the status of an existing FM ticket."""

    normalized_id = ticket_id.strip().upper()

    allowed_statuses = {
        "OPEN",
        "ASSIGNED",
        "IN_PROGRESS",
        "PENDING_VENDOR",
        "RESOLVED",
        "CLOSED",
        "REOPENED",
    }

    normalized_status = new_status.strip().upper()

    if normalized_status not in allowed_statuses:
        return {
            "success": False,
            "message": (
                f"Invalid status '{new_status}'. "
                f"Allowed statuses: "
                f"{', '.join(sorted(allowed_statuses))}"
            ),
        }

    query = (
        db.collection("tickets")
        .where(
            filter=firestore.FieldFilter(
                "ticket_id",
                "==",
                normalized_id,
            )
        )
        .limit(1)
        .stream()
    )

    documents = list(query)

    if not documents:
        return {
            "success": False,
            "message": (
                f"Ticket {normalized_id} was not found."
            ),
        }

    document = documents[0]
    existing_ticket = document.to_dict()

    current_status = existing_ticket.get("status")

    # ---------------------------------------------------------
    # PREVENT DUPLICATE STATUS UPDATE
    # ---------------------------------------------------------
    # Allow assignment/reassignment even when the lifecycle
    # status remains unchanged.
    if (
        current_status == normalized_status
        and not responsible_team.strip()
    ):
        return {
            "success": False,
            "ticket_id": normalized_id,
            "status": current_status,
            "responsible_team": existing_ticket.get(
                "responsible_team"
            ),
            "message": (
                f"Ticket {normalized_id} is already "
                f"{normalized_status}."
            ),
        }

    now = datetime.now(timezone.utc)

    updates = {
        "status": normalized_status,
        "updated_at": now,
    }

    if responsible_team.strip():
        updates["responsible_team"] = (
            responsible_team.strip()
        )

    # ---------------------------------------------------------
    # RESOLVED
    # ---------------------------------------------------------
    if normalized_status == "RESOLVED":
        updates["resolved_at"] = now
        updates["closed_at"] = None
        updates["escalation_status"] = "RESOLVED"

    # ---------------------------------------------------------
    # CLOSED
    # ---------------------------------------------------------
    elif normalized_status == "CLOSED":
        # Tickets must be RESOLVED before they can be CLOSED.
        if current_status != "RESOLVED":
            return {
                "success": False,
                "ticket_id": normalized_id,
                "status": current_status,
                "responsible_team": existing_ticket.get(
                    "responsible_team"
                ),
                "message": (
                    f"Ticket {normalized_id} cannot be closed "
                    f"because it is currently {current_status}. "
                    f"Tickets must be RESOLVED before closure."
                ),
            }

        resolved_at = existing_ticket.get("resolved_at")

        if not resolved_at:
            return {
                "success": False,
                "ticket_id": normalized_id,
                "status": current_status,
                "responsible_team": existing_ticket.get(
                    "responsible_team"
                ),
                "message": (
                    f"Ticket {normalized_id} cannot be closed "
                    f"because no resolution timestamp was found."
                ),
            }

        if resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(
                tzinfo=timezone.utc
            )

        working_days_elapsed = _working_days_elapsed(
            resolved_at,
            now,
        )

        if working_days_elapsed < 2:
            return {
                "success": False,
                "ticket_id": normalized_id,
                "status": current_status,
                "responsible_team": existing_ticket.get(
                    "responsible_team"
                ),
                "resolved_at": resolved_at.isoformat(),
                "working_days_elapsed": working_days_elapsed,
                "message": (
                    f"Ticket {normalized_id} cannot be closed yet. "
                    f"It has been resolved for "
                    f"{working_days_elapsed} working day(s). "
                    f"Closure is allowed after 2 working days."
                ),
            }

        updates["closed_at"] = now
        updates["escalation_status"] = "RESOLVED"

    # ---------------------------------------------------------
    # REOPENED
    # ---------------------------------------------------------
    elif normalized_status == "REOPENED":
        updates["escalation_status"] = "NOT_ESCALATED"

    document.reference.update(updates)

    # ---------------------------------------------------------
    # LOG STATUS CHANGE
    # ---------------------------------------------------------
    _log_ticket_event(
        ticket_id=normalized_id,
        event_type="STATUS_CHANGED",
        message=(
            f"Ticket {normalized_id} changed to "
            f"{normalized_status}."
        ),
        status=normalized_status,
    )

    final_team = (
        responsible_team.strip()
        if responsible_team.strip()
        else existing_ticket.get(
            "responsible_team"
        )
    )

    # ---------------------------------------------------------
    # AUTOMATIC REQUESTER NOTIFICATION ON RESOLUTION
    # ---------------------------------------------------------
    resolution_notification_created = False

    if normalized_status == "RESOLVED":
        requester = existing_ticket.get(
            "requester",
            "",
        )

        if requester and not _resolution_notification_exists(
            normalized_id
        ):
            notification = _create_resolution_notification(
                ticket_id=normalized_id,
                requester=requester,
                responsible_team=final_team or "",
            )

            if notification.get("success"):
                resolution_notification_created = True

                _log_ticket_event(
                    ticket_id=normalized_id,
                    event_type="REQUESTER_NOTIFIED",
                    message=(
                        f"Requester {requester} was notified "
                        f"that ticket {normalized_id} was resolved."
                    ),
                    status="RESOLVED",
                )

    return {
        "success": True,
        "ticket_id": normalized_id,
        "status": normalized_status,
        "responsible_team": final_team,
        "resolved_at": (
            now.isoformat()
            if normalized_status == "RESOLVED"
            else (
                existing_ticket.get(
                    "resolved_at"
                ).isoformat()
                if existing_ticket.get("resolved_at")
                else None
            )
        ),
        "closed_at": (
            now.isoformat()
            if normalized_status == "CLOSED"
            else None
        ),
        "resolution_notification_created": (
            resolution_notification_created
        ),
        "message": (
            f"Ticket {normalized_id} has been updated to "
            f"{normalized_status}."
        ),
    }


def _working_days_elapsed(
    start_time: datetime,
    end_time: datetime,
) -> int:
    """Calculate weekdays elapsed between two timestamps."""

    start_date = start_time.date()
    end_date = end_time.date()

    if end_date <= start_date:
        return 0

    elapsed_days = 0
    current_date = start_date

    while current_date < end_date:
        current_date += timedelta(days=1)

        if current_date.weekday() < 5:
            elapsed_days += 1

    return elapsed_days


def reopen_ticket(ticket_id: str) -> dict:
    """Reopen a resolved ticket within two working days."""

    normalized_id = ticket_id.strip().upper()

    query = (
        db.collection("tickets")
        .where(
            filter=firestore.FieldFilter(
                "ticket_id",
                "==",
                normalized_id,
            )
        )
        .limit(1)
        .stream()
    )

    documents = list(query)

    if not documents:
        return {
            "success": False,
            "message": (
                f"Ticket {normalized_id} was not found."
            ),
        }

    document = documents[0]
    ticket = document.to_dict()

    current_status = ticket.get("status")

    if current_status == "REOPENED":
        return {
            "success": False,
            "ticket_id": normalized_id,
            "status": "REOPENED",
            "message": (
                f"Ticket {normalized_id} is already REOPENED."
            ),
        }

    if current_status != "RESOLVED":
        return {
            "success": False,
            "ticket_id": normalized_id,
            "status": current_status,
            "message": (
                f"Ticket {normalized_id} cannot be reopened "
                f"because its current status is {current_status}."
            ),
        }

    resolved_at = ticket.get("resolved_at")

    if not resolved_at:
        return {
            "success": False,
            "ticket_id": normalized_id,
            "message": (
                f"Ticket {normalized_id} does not have "
                "a resolution timestamp."
            ),
        }

    now = datetime.now(timezone.utc)

    if resolved_at.tzinfo is None:
        resolved_at = resolved_at.replace(
            tzinfo=timezone.utc
        )

    working_days_elapsed = _working_days_elapsed(
        resolved_at,
        now,
    )

    if working_days_elapsed > 2:
        return {
            "success": False,
            "ticket_id": normalized_id,
            "status": current_status,
            "resolved_at": resolved_at.isoformat(),
            "working_days_elapsed": working_days_elapsed,
            "message": (
                f"Ticket {normalized_id} cannot be reopened "
                "because the 2-working-day reopening window "
                "has expired."
            ),
        }

    document.reference.update(
        {
            "status": "REOPENED",
            "updated_at": now,
            "escalation_status": "NOT_ESCALATED",
        }
    )

    _log_ticket_event(
        ticket_id=normalized_id,
        event_type="REOPENED",
        message=(
            f"Ticket {normalized_id} was reopened by the requester."
        ),
        status="REOPENED",
    )

    return {
        "success": True,
        "ticket_id": normalized_id,
        "status": "REOPENED",
        "resolved_at": resolved_at.isoformat(),
        "working_days_elapsed": working_days_elapsed,
        "message": (
            f"Ticket {normalized_id} has been reopened "
            "within the 2-working-day window."
        ),
    }


def list_my_tickets(
    requester: str = "Demo User",
) -> dict:
    """Return the user's service tickets from Firestore."""

    documents = (
        db.collection("tickets")
        .where("requester", "==", requester)
        .stream()
    )

    tickets = []

    for document in documents:

        ticket = document.to_dict()

        ticket["document_id"] = document.id

        for key, value in list(ticket.items()):

            if hasattr(value, "isoformat"):
                ticket[key] = value.isoformat()

        tickets.append(ticket)

    tickets.sort(
        key=lambda ticket: ticket.get(
            "created_at",
            "",
        ),
        reverse=True,
    )

    return {
        "success": True,
        "requester": requester,
        "total_tickets": len(tickets),
        "tickets": tickets,
    }

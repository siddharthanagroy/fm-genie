from datetime import datetime, timezone

from google.cloud import firestore

from .notification_tools import create_notification


db = firestore.Client()


def _get_warning_seconds(sla: str) -> int:
    """Return an appropriate warning threshold for an SLA."""

    value = sla.strip().lower()

    if value == "immediate":
        return 0

    if "minute" in value:
        minutes = int(value.split()[0])
        return max(60, int(minutes * 60 * 0.33))

    if "hour" in value:
        hours = int(value.split()[0])
        return int(hours * 60 * 60 * 0.25)

    if "working day" in value:
        days = int(value.split()[0])
        return int(days * 8 * 60 * 60 * 0.25)

    return 3600


def _log_escalation_event(
    ticket_id: str,
    event_type: str,
    message: str,
    status: str,
) -> None:
    """Record an SLA/escalation event in Firestore."""

    now = datetime.now(timezone.utc)

    event = {
        "ticket_id": ticket_id,
        "event_type": event_type,
        "message": message,
        "status": status,
        "actor": "FM Genie SLA Monitor",
        "created_at": now,
    }

    db.collection("ticket_events").add(event)


def _create_sla_notification(
    ticket_id: str,
    recipient: str,
    notification_type: str,
    message: str,
) -> None:
    """Create an SLA notification."""

    try:
        create_notification(
            ticket_id=ticket_id,
            recipient=recipient,
            notification_type=notification_type,
            message=message,
        )
    except Exception as exc:
        # Notification failure should not prevent SLA monitoring.
        print(
            f"Warning: notification creation failed for "
            f"{ticket_id}: {exc}"
        )


def check_sla_status() -> dict:
    """Check SLA status for all active FM tickets.

    Returns:
        A dictionary containing the SLA state of active tickets.

    SLA states:
        ON_TRACK
        APPROACHING_SLA
        SLA_BREACHED
        SAFETY_CRITICAL
        NO_SLA
    """

    now = datetime.now(timezone.utc)

    documents = (
        db.collection("tickets")
        .where(
            filter=firestore.FieldFilter(
                "status",
                "not-in",
                ["CLOSED", "RESOLVED"],
            )
        )
        .stream()
    )

    results = []

    for document in documents:
        ticket = document.to_dict()

        ticket_id = ticket.get("ticket_id")
        status = ticket.get("status")
        priority = ticket.get("priority")
        sla = ticket.get("sla", "")
        sla_due_at = ticket.get("sla_due_at")
        safety_critical = ticket.get(
            "safety_critical",
            False,
        )
        escalation_status = ticket.get(
            "escalation_status",
            "NOT_ESCALATED",
        )

        responsible_team = ticket.get(
            "responsible_team",
            "FM Operations",
        )

        # -----------------------------------------------------
        # SAFETY CRITICAL
        # -----------------------------------------------------
        if safety_critical:
            results.append(
                {
                    "ticket_id": ticket_id,
                    "status": status,
                    "priority": priority,
                    "sla": sla,
                    "sla_status": "SAFETY_CRITICAL",
                    "sla_due_at": (
                        sla_due_at.isoformat()
                        if sla_due_at
                        else None
                    ),
                    "escalation_status": escalation_status,
                    "message": (
                        f"Ticket {ticket_id} is safety critical "
                        "and requires immediate attention."
                    ),
                }
            )
            continue

        # -----------------------------------------------------
        # NO SLA
        # -----------------------------------------------------
        if not sla_due_at:
            results.append(
                {
                    "ticket_id": ticket_id,
                    "status": status,
                    "priority": priority,
                    "sla": sla,
                    "sla_status": "NO_SLA",
                    "sla_due_at": None,
                    "escalation_status": escalation_status,
                    "message": (
                        f"Ticket {ticket_id} does not have "
                        "an SLA due time."
                    ),
                }
            )
            continue

        # -----------------------------------------------------
        # SLA BREACHED
        # -----------------------------------------------------
        if now >= sla_due_at:
            sla_status = "SLA_BREACHED"

            # Avoid repeatedly writing escalation events
            # and notifications.
            if escalation_status != "BREACHED":
                document.reference.update(
                    {
                        "escalation_status": "BREACHED",
                        "updated_at": now,
                    }
                )

                breach_message = (
                    f"Ticket {ticket_id} has breached its "
                    f"{sla} SLA and requires escalation."
                )

                _log_escalation_event(
                    ticket_id=ticket_id,
                    event_type="SLA_BREACHED",
                    message=breach_message,
                    status=status,
                )

                _create_sla_notification(
                    ticket_id=ticket_id,
                    recipient="FM Admin",
                    notification_type="SLA_BREACH",
                    message=breach_message,
                )

                escalation_status = "BREACHED"

        else:
            remaining_seconds = (
                sla_due_at - now
            ).total_seconds()

            warning_seconds = _get_warning_seconds(sla)

            if remaining_seconds <= warning_seconds:
                sla_status = "APPROACHING_SLA"

                # Record the warning only once.
                if escalation_status == "NOT_ESCALATED":
                    document.reference.update(
                        {
                            "escalation_status": "APPROACHING",
                            "updated_at": now,
                        }
                    )

                    warning_message = (
                        f"Ticket {ticket_id} is approaching "
                        f"its {sla} SLA deadline."
                    )

                    _log_escalation_event(
                        ticket_id=ticket_id,
                        event_type="SLA_WARNING",
                        message=warning_message,
                        status=status,
                    )

                    _create_sla_notification(
                        ticket_id=ticket_id,
                        recipient=responsible_team,
                        notification_type="SLA_WARNING",
                        message=warning_message,
                    )

                    escalation_status = "APPROACHING"

            else:
                sla_status = "ON_TRACK"

        results.append(
            {
                "ticket_id": ticket_id,
                "status": status,
                "priority": priority,
                "sla": sla,
                "sla_status": sla_status,
                "sla_due_at": sla_due_at.isoformat(),
                "escalation_status": escalation_status,
                "message": (
                    f"Ticket {ticket_id} is currently "
                    f"{sla_status}."
                ),
            }
        )

    return {
        "success": True,
        "checked_at": now.isoformat(),
        "ticket_count": len(results),
        "tickets": results,
    }

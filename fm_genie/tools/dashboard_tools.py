from collections import Counter
from datetime import datetime, timezone

from google.cloud import firestore


db = firestore.Client()


def get_fm_dashboard() -> dict:
    """Return an FM operational KPI dashboard from Firestore."""

    now = datetime.now(timezone.utc)

    documents = db.collection("tickets").stream()

    tickets = [document.to_dict() for document in documents]

    status_counter = Counter()
    category_counter = Counter()
    team_counter = Counter()

    safety_critical_count = 0
    sla_breached_count = 0
    sla_approaching_count = 0
    sla_on_track_count = 0
    no_sla_count = 0

    active_statuses = {
        "OPEN",
        "ASSIGNED",
        "IN_PROGRESS",
        "PENDING_VENDOR",
        "REOPENED",
    }

    active_ticket_count = 0

    for ticket in tickets:
        status = ticket.get("status", "UNKNOWN")
        category = ticket.get("category", "Unknown")

        team = ticket.get("responsible_team") or "Unassigned"

        status_counter[status] += 1
        category_counter[category] += 1
        team_counter[team] += 1

        if status in active_statuses:
            active_ticket_count += 1

        if ticket.get("safety_critical", False):
            safety_critical_count += 1

        sla_due_at = ticket.get("sla_due_at")

        if not sla_due_at:
            no_sla_count += 1
            continue

        if ticket.get("safety_critical", False):
            continue

        if status in {"RESOLVED", "CLOSED"}:
            continue

        if now >= sla_due_at:
            sla_breached_count += 1
            continue

        sla = str(ticket.get("sla", "")).lower()

        warning_seconds = 3600

        if "hour" in sla:
            try:
                hours = int(sla.split()[0])
                warning_seconds = int(
                    hours * 60 * 60 * 0.25
                )
            except (ValueError, IndexError):
                pass

        elif "minute" in sla:
            try:
                minutes = int(sla.split()[0])
                warning_seconds = max(
                    60,
                    int(minutes * 60 * 0.33)
                )
            except (ValueError, IndexError):
                pass

        remaining_seconds = (
            sla_due_at - now
        ).total_seconds()

        if remaining_seconds <= warning_seconds:
            sla_approaching_count += 1
        else:
            sla_on_track_count += 1

    return {
        "success": True,
        "generated_at": now.isoformat(),

        "total_tickets": len(tickets),

        "active_tickets": active_ticket_count,

        "status_counts": {
            "OPEN": status_counter.get("OPEN", 0),
            "ASSIGNED": status_counter.get("ASSIGNED", 0),
            "IN_PROGRESS": status_counter.get(
                "IN_PROGRESS",
                0,
            ),
            "PENDING_VENDOR": status_counter.get(
                "PENDING_VENDOR",
                0,
            ),
            "REOPENED": status_counter.get(
                "REOPENED",
                0,
            ),
            "RESOLVED": status_counter.get(
                "RESOLVED",
                0,
            ),
            "CLOSED": status_counter.get(
                "CLOSED",
                0,
            ),
        },

        "sla_summary": {
            "safety_critical": safety_critical_count,
            "sla_breached": sla_breached_count,
            "sla_approaching": sla_approaching_count,
            "sla_on_track": sla_on_track_count,
            "no_sla": no_sla_count,
        },

        "category_counts": dict(category_counter),

        "team_workload": dict(team_counter),

        "message": (
            "FM dashboard generated successfully."
        ),
    }

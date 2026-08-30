import os
import requests
from collections import Counter
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from google.cloud import firestore

app = Flask(__name__)

API_BASE = "https://fm-genie-ffp75lvgda-el.a.run.app"

# Direct Firestore client for read-only dashboard data.
db = firestore.Client()

@app.route("/")
def index():
    return send_from_directory(".", "index.html")



@app.route("/api/notifications/latest", methods=["GET"])
def latest_notification():
    """Return the latest FM Genie notification directly from Firestore."""

    try:
        documents = (
            db.collection("notifications")
            .order_by(
                "created_at",
                direction=firestore.Query.DESCENDING,
            )
            .limit(1)
            .stream()
        )

        document = next(iter(documents), None)

        if document is None:
            return jsonify({
                "success": True,
                "notification": None,
                "message": "No notifications found.",
            })

        data = document.to_dict()

        created_at = data.get("created_at")

        return jsonify({
            "success": True,
            "notification": {
                "notification_id": document.id,
                "ticket_id": data.get("ticket_id"),
                "recipient": data.get("recipient"),
                "notification_type": data.get(
                    "notification_type"
                ),
                "message": data.get("message"),
                "status": data.get("status"),
                "created_at": (
                    created_at.isoformat()
                    if created_at
                    else None
                ),
            },
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Return FM dashboard KPIs directly from Firestore."""

    try:
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
            status = str(
                ticket.get("status", "UNKNOWN")
            ).upper()

            category = (
                ticket.get("category")
                or "Unknown"
            )

            team = (
                ticket.get("responsible_team")
                or "Unassigned"
            )

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

            sla = str(
                ticket.get("sla", "")
            ).lower()

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

        return jsonify({
            "success": True,
            "generated_at": now.isoformat(),
            "total_tickets": len(tickets),
            "active_tickets": active_ticket_count,

            "status_counts": {
                "OPEN": status_counter.get("OPEN", 0),
                "ASSIGNED": status_counter.get("ASSIGNED", 0),
                "IN_PROGRESS": status_counter.get(
                    "IN_PROGRESS", 0
                ),
                "PENDING_VENDOR": status_counter.get(
                    "PENDING_VENDOR", 0
                ),
                "REOPENED": status_counter.get(
                    "REOPENED", 0
                ),
                "RESOLVED": status_counter.get(
                    "RESOLVED", 0
                ),
                "CLOSED": status_counter.get(
                    "CLOSED", 0
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
                "FM dashboard read directly from Firestore."
            ),
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy(path):
    # The ADK API server exposes /run directly.
    # Keep the frontend's /api/run contract and translate it here.
    if path == "run":
        url = f"{API_BASE}/run"
    else:
        url = f"{API_BASE}/{path}"

    try:
        response = requests.request(
            method=request.method,
            url=url,
            headers={
                "Content-Type": request.headers.get("Content-Type", "application/json")
            },
            data=request.get_data(),
            timeout=120,
        )

        return (
            response.content,
            response.status_code,
            {"Content-Type": response.headers.get("Content-Type", "application/json")}
        )

    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

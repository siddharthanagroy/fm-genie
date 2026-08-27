from datetime import datetime, timezone

from google.cloud import firestore


db = firestore.Client()


def create_notification(
    ticket_id: str,
    recipient: str,
    notification_type: str,
    message: str,
) -> dict:
    """Create a notification record for an FM ticket."""

    now = datetime.now(timezone.utc)

    notification = {
        "ticket_id": ticket_id.strip().upper(),
        "recipient": recipient.strip(),
        "notification_type": notification_type.strip().upper(),
        "message": message.strip(),
        "status": "PENDING",
        "created_at": now,
    }

    notification_ref = db.collection("notifications").add(
        notification
    )

    return {
        "success": True,
        "notification_id": notification_ref[1].id,
        "ticket_id": notification["ticket_id"],
        "recipient": notification["recipient"],
        "notification_type": notification["notification_type"],
        "status": "PENDING",
        "message": "Notification created successfully.",
    }


def get_ticket_notifications(ticket_id: str) -> dict:
    """Retrieve all notifications associated with a ticket."""

    normalized_id = ticket_id.strip().upper()

    documents = (
        db.collection("notifications")
        .where(
            filter=firestore.FieldFilter(
                "ticket_id",
                "==",
                normalized_id,
            )
        )
        .stream()
    )

    notifications = []

    for document in documents:
        notification = document.to_dict()

        notifications.append(
            {
                "notification_id": document.id,
                "ticket_id": notification.get("ticket_id"),
                "recipient": notification.get("recipient"),
                "notification_type": notification.get(
                    "notification_type"
                ),
                "message": notification.get("message"),
                "status": notification.get("status"),
                "created_at": (
                    notification.get("created_at").isoformat()
                    if notification.get("created_at")
                    else None
                ),
            }
        )

    return {
        "success": True,
        "ticket_id": normalized_id,
        "notification_count": len(notifications),
        "notifications": notifications,
    }

# FM SLA and TAT rules.
#
# These are prototype business rules for the hackathon.
# They are intentionally deterministic so the LLM does not invent
# operational SLA commitments.


SLA_RULES = {
    "Electrical": {
        "Critical": {"response": "15 minutes", "resolution": "2 hours"},
        "High": {"response": "30 minutes", "resolution": "4 hours"},
        "Medium": {"response": "1 hour", "resolution": "8 hours"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "Plumbing": {
        "Critical": {"response": "15 minutes", "resolution": "2 hours"},
        "High": {"response": "30 minutes", "resolution": "4 hours"},
        "Medium": {"response": "1 hour", "resolution": "8 hours"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "HVAC": {
        "Critical": {"response": "15 minutes", "resolution": "2 hours"},
        "High": {"response": "30 minutes", "resolution": "4 hours"},
        "Medium": {"response": "1 hour", "resolution": "8 hours"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "Housekeeping": {
        "Critical": {"response": "30 minutes", "resolution": "2 hours"},
        "High": {"response": "1 hour", "resolution": "4 hours"},
        "Medium": {"response": "2 hours", "resolution": "8 hours"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "Cafeteria": {
        "Critical": {"response": "30 minutes", "resolution": "2 hours"},
        "High": {"response": "1 hour", "resolution": "4 hours"},
        "Medium": {"response": "2 hours", "resolution": "4 hours"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "Security": {
        "Critical": {"response": "Immediate", "resolution": "1 hour"},
        "High": {"response": "15 minutes", "resolution": "2 hours"},
        "Medium": {"response": "30 minutes", "resolution": "4 hours"},
        "Low": {"response": "2 hours", "resolution": "1 working day"},
    },
    "Access Control": {
        "Critical": {"response": "15 minutes", "resolution": "2 hours"},
        "High": {"response": "30 minutes", "resolution": "4 hours"},
        "Medium": {"response": "1 hour", "resolution": "8 hours"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "Civil / Building": {
        "Critical": {"response": "30 minutes", "resolution": "4 hours"},
        "High": {"response": "1 hour", "resolution": "8 hours"},
        "Medium": {"response": "2 hours", "resolution": "1 working day"},
        "Low": {"response": "4 hours", "resolution": "3 working days"},
    },
    "Pest Control": {
        "Critical": {"response": "30 minutes", "resolution": "4 hours"},
        "High": {"response": "1 hour", "resolution": "8 hours"},
        "Medium": {"response": "2 hours", "resolution": "1 working day"},
        "Low": {"response": "4 hours", "resolution": "3 working days"},
    },
    "Workplace / General": {
        "Critical": {"response": "30 minutes", "resolution": "4 hours"},
        "High": {"response": "1 hour", "resolution": "8 hours"},
        "Medium": {"response": "2 hours", "resolution": "1 working day"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
    "Other": {
        "Critical": {"response": "30 minutes", "resolution": "4 hours"},
        "High": {"response": "1 hour", "resolution": "8 hours"},
        "Medium": {"response": "2 hours", "resolution": "1 working day"},
        "Low": {"response": "4 hours", "resolution": "2 working days"},
    },
}


def get_sla(category: str, priority: str) -> dict:
    """Return the deterministic SLA for a category and priority."""

    category_key = category.strip()
    priority_key = priority.strip().title()

    category_rules = SLA_RULES.get(category_key, SLA_RULES["Other"])

    return category_rules.get(
        priority_key,
        category_rules["Medium"],
    )

"""
Safety-critical FM rules.

These rules take precedence over normal category, priority, and SLA rules.

These are prototype rules for the hackathon and should be validated against
the organization's official EHS/FM emergency procedures before production use.
"""


SAFETY_RULES = {
    # Fire / smoke
    "fire": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Fire Safety Team",
    },
    "smoke": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Fire Safety Team",
    },
    "burning smell": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Fire Safety Team",
    },

    # Electrical safety
    "electric shock": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Electrical Safety Team",
    },
    "electrical shock": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Electrical Safety Team",
    },
    "sparking": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Electrical Safety Team",
    },
    "sparks": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Electrical Safety Team",
    },
    "exposed live wire": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Electrical Safety Team",
    },
    "live wire": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Electrical Safety Team",
    },

    # Ceiling / structural hazards
    "ceiling collapse": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "ceiling collapsing": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "ceiling falling": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "falling ceiling": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "ceiling is falling": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "ceiling pieces falling": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "ceiling debris": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "falling debris": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "structural damage": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },
    "structural failure": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Building Safety Team",
    },

    # Gas / chemical hazards
    "gas leak": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Safety Team",
    },
    "gas smell": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Safety Team",
    },
    "chemical leak": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Safety Team",
    },

    # Lift / elevator emergencies
    "person trapped in lift": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Lift Rescue Team",
    },
    "person trapped in elevator": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Lift Rescue Team",
    },
    "stuck in lift": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Lift Rescue Team",
    },
    "stuck in elevator": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Lift Rescue Team",
    },

    # Injury / emergency access
    "injury": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Safety Team",
    },
    "injured": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Safety Team",
    },
    "emergency exit blocked": {
        "priority": "Critical",
        "response": "Immediate",
        "escalation": "Emergency / Safety Team",
    },
}


def detect_safety_risk(issue_description: str) -> dict:
    """Detect potential immediate safety risks in an FM request."""

    text = issue_description.lower()

    # Check more specific phrases first.
    for trigger, rule in SAFETY_RULES.items():
        if trigger in text:
            return {
                "is_safety_critical": True,
                "trigger": trigger,
                "priority": rule["priority"],
                "response": rule["response"],
                "escalation": rule["escalation"],
            }

    return {
        "is_safety_critical": False,
        "trigger": "",
        "priority": "",
        "response": "",
        "escalation": "",
    }

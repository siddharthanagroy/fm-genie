from fm_genie.rules.safety_rules import detect_safety_risk

tests = [
    "Coffee machine is not working",
    "There are sparks from an exposed live wire and an employee received an electric shock",
    "The ceiling is falling and pieces are coming down",
    "There is smoke coming from the electrical panel",
]

for issue in tests:
    print("\nISSUE:", issue)
    print(detect_safety_risk(issue))

from app import safety_net, build_prompt

PROFILE = {"name": "Maya", "allergens": {"peanuts": ["peanut", "satay"], "shellfish": ["shrimp"]}}

dishes = safety_net([
    {"name": "Green salad", "menu_text": "greens, lemon", "verdict": "safe", "reason": "", "ask_server": ""},
    {"name": "Chicken Satay", "menu_text": "grilled skewers", "verdict": "safe", "reason": "", "ask_server": ""},
    {"name": "Curry", "menu_text": "coconut", "verdict": "maybe?", "reason": "", "ask_server": ""},
], PROFILE)

by = {d["name"]: d for d in dishes}
assert by["Chicken Satay"]["verdict"] == "avoid", "keyword net must override a model 'safe'"
assert "peanuts" in by["Chicken Satay"]["reason"]
assert by["Curry"]["verdict"] == "ask", "unknown verdicts must never be treated as safe"
assert by["Green salad"]["verdict"] == "safe"
assert [d["verdict"] for d in dishes] == ["avoid", "ask", "safe"], "dangerous dishes sort first"
assert "peanuts, shellfish" in build_prompt(PROFILE, "x")
print("ok")

from app import parse_dishes
assert parse_dishes('Sure!\n```json\n{"dishes": [{"name": "Rice"}]}\n```')[0]["name"] == "Rice"
print("parse ok")

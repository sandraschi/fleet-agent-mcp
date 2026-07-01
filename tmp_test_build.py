"""Debug: simulate what build_app does and check seed."""
import sys
sys.path.insert(0, "src")
import os
from pathlib import Path

# Clean start
db = Path.home() / ".fleet-agent" / "fleet-agent.db"
if db.exists():
    db.unlink()

# Build the app
from fleet_agent.server import build_app
app = build_app()

# Check cards
from fleet_agent.engine.sqlite_store import get_store
s = get_store()
cards = s.cards_list()
print(f"Cards: {len(cards)}")
for c in cards:
    print(f"  [{c['id']}] {c['title']}")
scripts = s.script_list()
print(f"Scripts: {len(scripts)}")
for sc in scripts:
    print(f"  {sc['name']} ({sc['language']})")

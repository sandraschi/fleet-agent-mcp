"""Exact simulation of build_app sequence."""
import sys
sys.path.insert(0, "src")
from pathlib import Path

# Wipe DB
db = Path.home() / ".fleet-agent" / "fleet-agent.db"
if db.exists():
    db.unlink()

# Import and run exact sequence
from fleet_agent.config import settings
settings.ensure_dirs()

from fleet_agent.engine.sqlite_store import get_store
from fleet_agent.coworker.bootstrap import ensure_coworker_tasks
from fleet_agent.coworker.seed import seed_cards_and_scripts

# Step 1: ensure_coworker_tasks (as in build_app)
boot = ensure_coworker_tasks()
print("Bootstrap:", boot["seeded"])

# Step 2: seed (as in build_app)
seeded = seed_cards_and_scripts()
print("Seed:", seeded["message"])

# Step 3: Read from health-check pattern (as in api_health)
store2 = get_store()  # singleton — same as bootstrap/seed used
cards = store2.cards_list()
print(f"Cards from get_store() singleton: {len(cards)}")
for c in cards:
    print(f"  {c['title']}")

# Step 4: Read directly from DB
import sqlite3
conn = sqlite3.connect(str(settings.db_path))
rows = conn.execute("SELECT count(*) FROM memory_cards").fetchone()
print(f"Cards from direct SQL: {rows[0]}")
conn.close()

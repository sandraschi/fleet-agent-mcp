"""Debug seed."""
import sys
sys.path.insert(0, "src")
from fleet_agent.engine.sqlite_store import get_store
from fleet_agent.config import settings
from fleet_agent.coworker.seed import seed_cards_and_scripts

db = settings.db_path
if db.exists():
    db.unlink()
settings.ensure_dirs()

r = seed_cards_and_scripts()
print("Seed result:", r)

s = get_store()
cards = s.cards_list()
print("Cards after seed:", len(cards))
for c in cards:
    print(" -", c["title"])

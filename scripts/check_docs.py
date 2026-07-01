"""Check Fritz memory and evolution."""
import json

import httpx

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

def f(tool, args):
    p = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": tool, "arguments": args}, "id": 1}
    r = httpx.post(url, json=p, headers=H, timeout=15)
    for line in r.text.splitlines():
        if line.startswith("data: "):
            sc = json.loads(line[6:]).get("result", {}).get("structuredContent") or {}
            print(json.dumps(sc, indent=2)[:2000])

print("=== PROJECT NOTES ===")
f("memory_project_notes", {"project": "fritz-test"})
print("\n=== EVOLUTION LOG ===")
f("evolution_list", {"limit": 10})

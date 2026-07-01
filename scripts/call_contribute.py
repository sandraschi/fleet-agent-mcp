"""Sic Fritz on Stephan's repo autonomously."""
import json

import httpx

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

p = {
    "jsonrpc": "2.0", "method": "tools/call",
    "params": {
        "name": "fritz_contribute",
        "arguments": {
            "repo_url": "https://github.com/StephanSchipal/edge-bookmark-mcp-server",
            "dry_run": False,
        },
    },
    "id": 1,
}

print("Calling fritz_contribute... (this may take 1-2 minutes)")
r = httpx.post(url, json=p, headers=H, timeout=300)
for line in r.text.splitlines():
    if line.startswith("data: "):
        d = json.loads(line[6:])
        sc = d.get("result", {}).get("structuredContent", {})
        print(json.dumps(sc, indent=2))

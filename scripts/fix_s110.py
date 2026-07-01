"""Fix S110 bare except-pass in discord-mcp via Fritz file_edit."""
import json

import httpx

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

old = "            except Exception:\n                pass"
new = '            except Exception as e2:\n                logger.warning("Failed to read error body: %s", e2)'

p = {
    "jsonrpc": "2.0", "method": "tools/call",
    "params": {
        "name": "file_edit",
        "arguments": {
            "path": "D:/Dev/repos/discord-mcp/src/discord_mcp/sampling/discord_sampling_handler.py",
            "old_string": old,
            "new_string": new,
        },
    },
    "id": 1,
}
r = httpx.post(url, json=p, headers=H, timeout=15)
for line in r.text.splitlines():
    if line.startswith("data: "):
        d = json.loads(line[6:]).get("result", {}).get("structuredContent", {})
        print(json.dumps(d, indent=2))

"""Fix S701 jinja2 autoescape via Fritz file_edit."""
import json

import httpx

H = {"Accept": "application/json, text/event-stream"}
url = "http://127.0.0.1:10996/mcp/"

old = "            self.template_env = Environment(loader=TemplateLoader(self.templates))"
new = '            self.template_env = Environment(loader=TemplateLoader(self.templates), autoescape=True)'

p = {
    "jsonrpc": "2.0", "method": "tools/call",
    "params": {
        "name": "file_edit",
        "arguments": {"path": "D:/Dev/repos/edge-bookmark-mcp-server/src/exporter.py", "old_string": old, "new_string": new},
    },
    "id": 1,
}
r = httpx.post(url, json=p, headers=H, timeout=15)
for line in r.text.splitlines():
    if line.startswith("data: "):
        d = json.loads(line[6:]).get("result", {}).get("structuredContent", {})
        print(json.dumps(d, indent=2))

"""Test Fritz code generation via LM Studio."""
import json

import httpx

H = {"Accept": "application/json, text/event-stream"}
payload = {
    "jsonrpc": "2.0", "method": "tools/call",
    "params": {
        "name": "code_generate",
        "arguments": {
            "spec": "Write a Python function greet(name: str) -> str that returns Hello, {name}!",
            "repo_path": "D:/Dev/repos/fritz-test",
            "file_path": "src/fritz_test/greeter.py",
            "context": "simple function",
        },
    },
    "id": 1,
}
r = httpx.post("http://127.0.0.1:10996/mcp/", json=payload, headers=H, timeout=180)
for line in r.text.splitlines():
    if line.startswith("data: "):
        d = json.loads(line[6:])
        print(json.dumps(d, indent=2))

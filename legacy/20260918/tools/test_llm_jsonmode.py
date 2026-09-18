"""Test whether the endpoint supports response_format json_object."""
import json
import urllib.request
from pathlib import Path
import re

key = None
cred = Path.home() / ".dsh" / ".credentials.yaml"
m = re.search(r'CORP_AI_API_KEY:\s*["\']?([^"\'\s]+)', cred.read_text(encoding="utf-8"))
key = m.group(1) if m else None

body = {
    "model": "corp-ai/openai/deepseek-v4-pro",
    "messages": [{"role": "user",
                  "content": 'Return a JSON object with a "type" field equal to "DISPATCH" and a "reason" field.'}],
    "max_tokens": 512,
    "temperature": 0,
    "response_format": {"type": "json_object"},
}
req = urllib.request.Request(
    "http://192.168.27.4:18888/v1/chat/completions",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    print("content:", repr(data["choices"][0]["message"]["content"]))
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    if hasattr(e, "read"):
        print(e.read().decode("utf-8", "replace")[:800])

"""Test the corp-ai OpenAI-compatible endpoint used by the LLM manager."""
import json
import re
import sys
import urllib.request
from pathlib import Path

CRED = Path(r"C:\Users\user\.dsh\.credentials.yaml").read_text(encoding="utf-8")
m = re.search(r'CORP_AI_API_KEY:\s*["\']?([^"\'\s]+)', CRED)
key = m.group(1) if m else None
if not key:
    print("NO API KEY FOUND")
    sys.exit(2)

BASE = "http://192.168.27.4:18888/v1"
model = sys.argv[1] if len(sys.argv) > 1 else "corp-ai/openai/deepseek-v4-pro"

body = {
    "model": model,
    "messages": [{"role": "user", "content": "Reply with exactly this JSON and nothing else: {\"ok\": true}"}],
    "max_tokens": 64,
    "temperature": 0,
}
req = urllib.request.Request(
    f"{BASE}/chat/completions",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
    print("model reported:", data.get("model"))
    print("content:", repr(data["choices"][0]["message"]["content"]))
    usage = data.get("usage", {})
    print("usage:", usage)
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    sys.exit(1)

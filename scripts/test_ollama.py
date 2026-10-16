"""Smoke test: send one real request through Kaushora's Ollama-backed ask_ai().

Usage: python scripts/test_ollama.py
Reads OLLAMA_API_KEY from .env (loaded by app.py's load_dotenv) or the shell env.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("OLLAMA_API_KEY", "").strip()
model = os.environ.get("OLLAMA_MODEL", "gemma4:31b")

if not key:
    print("OLLAMA_API_KEY is missing or empty.")
    print("Save your key in .env as: OLLAMA_API_KEY=<your key>  (line 4)")
    sys.exit(1)

print(f"Key present (length {len(key)}). Sending real request to Ollama with model {model} ...")

url = "https://ollama.com/api/chat"
body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "Reply with exactly: KAUSHORA_OLLAMA_OK"}],
    "stream": False,
}).encode()
req = urllib.request.Request(url, data=body, headers={
    "Content-Type": "application/json",
    "Authorization": "Bearer " + key,
}, method="POST")

try:
    with urllib.request.urlopen(req, timeout=90) as r:
        j = json.loads(r.read().decode())
    print("HTTP OK. Ollama reply:")
    print(j["message"]["content"])
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:400]}")
    if e.code == 401:
        print("-> Key wrong or missing.")
    elif e.code == 402:
        print("-> Model not in plan; stop.")
    elif e.code == 404:
        print("-> Model name wrong.")
    elif e.code == 429:
        print("-> Usage limit reached; stop.")
    sys.exit(1)
except Exception as e:
    print(f"{type(e).__name__}: {e}")
    sys.exit(1)

print("\nNow exercising the app's own ask_ai() code path ...")
from services.ai_service import ask_ai

res = ask_ai("How many job postings are in the dataset?")
print("ai_available:", res.get("ai_available"))
print("note:", res.get("note"))
print("answer (first 300 chars):", (res.get("answer") or "")[:300])

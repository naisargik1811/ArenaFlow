"""Probe the NVIDIA API key + model without starting the app.

Usage:
    .venv/bin/python check_nvidia.py
Reads NVIDIA_API_KEY / NVIDIA_MODEL from .env (or the environment).
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"


def main() -> int:
    load_dotenv()
    key = os.getenv("NVIDIA_API_KEY")
    model = os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)

    if not key:
        print("FAIL: NVIDIA_API_KEY is not set (check .env or environment).")
        return 1

    print(f"Probing model '{model}' at {NVIDIA_URL} ...")
    try:
        r = httpx.post(
            NVIDIA_URL,
            timeout=15.0,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with one word: ok"}],
                "max_tokens": 8,
            },
        )
    except httpx.HTTPError as exc:
        print(f"FAIL: network/request error -> {exc}")
        return 1

    print(f"status: {r.status_code}")
    if r.status_code != 200:
        print("FAIL: non-200 response")
        print(r.text[:600])
        return 1
    try:
        text = r.json()["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError) as exc:
        print(f"FAIL: unexpected response shape ({exc})")
        print(r.text[:600])
        return 1
    print(f"OK: model responded -> {text!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

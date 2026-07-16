"""LLM client with deterministic offline fallback.

Online:  POST https://integrate.api.nvidia.com/v1/chat/completions (NVIDIA NIM, OpenAI-compatible)
Offline: template the retrieved snippets into a useful answer.

Same shape in both cases - the caller doesn't need to branch.
"""

from __future__ import annotations
import json
import os
import unicodedata
from typing import Any

from pydantic import BaseModel

import httpx

from arenaflow.data.kb import Snippet
from arenaflow.core.retriever import _WORD, build_context

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
TIMEOUT_S = 12.0


SYSTEM_FAN = (
    "You are ArenaFlow, a multilingual fan concierge for the FIFA World Cup 2026. "
    "Reply in the user's language. Be concise (<= 90 words), friendly, and grounded in the "
    "REFERENCE NOTES. Use 2-4 short bullets when helpful. If accessibility or transport is "
    "asked about, give the exact station/line. Don't invent venues."
)

SYSTEM_OPS = (
    "You are ArenaFlow Ops, an operations co-pilot for stadium and event staff during the "
    "FIFA World Cup 2026. Use LIVE SNAPSHOT and REFERENCE NOTES. Be terse, decisive, and "
    "prioritise safety. Reply in plain text with short sections: Situation, Recommend, "
    "Risks. <= 130 words."
)


class Reply(BaseModel):
    text: str
    source: str  # "nvidia" | "offline"
    model: str | None
    used_ids: list[str]


def _format_offline_fan(query: str, snippets: list[Snippet]) -> str:
    if not snippets:
        return (
            "I don't have a specific answer for that, but the Guest Services desk at the "
            "nearest gate can help in 9 languages including sign language."
        )
    head = "Here's what I found for you:"
    bullets = []
    for s in snippets[:3]:
        first = s.text.split(". ")[0]
        bullets.append(f"- {first}.")
    extras = "Ask me for the gate, transit line, or accessibility feature you need."
    return f"{head}\n" + "\n".join(bullets) + f"\n{extras}"


def _format_offline_ops(snippet_summary: str, snapshot_json: str) -> str:
    return (
        "Situation: " + snippet_summary + "\n"
        "Recommend: brief fans to lowest-wait gate; keep transit in load-balancing mode.\n"
        "Risks: re-entry surge at halftime; monitor weather & AQI.\n"
        f"Snapshot: {snapshot_json[:300]}"
    )


async def _post_chat(
    api_key: str,
    model: str,
    system: str,
    user: str,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        r = await client.post(NVIDIA_URL, headers=headers, content=json.dumps(payload))
        r.raise_for_status()
        data = r.json()
    text = data["choices"][0]["message"]["content"]
    if not text or not text.strip():
        raise ValueError("empty completion from model")
    return text.strip()


async def _try_online(
    api_key: str | None,
    model: str,
    system: str,
    user: str,
    used_ids: list[str],
) -> Reply | None:
    """Best-effort online call; None on any transport/shape failure (caller falls back)."""
    if not api_key:
        return None
    try:
        text = await _post_chat(api_key, model, system, user)
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        # transport error, non-JSON body, or unexpected shape -> fall back
        return None
    return Reply(text=text.strip(), source="nvidia", model=model, used_ids=used_ids)


async def fan_reply(
    query: str,
    snippets: list[Snippet],
    api_key: str | None,
    model: str = DEFAULT_MODEL,
    language: str = "en",
) -> Reply:
    used = [s.id for s in snippets]
    ctx = build_context(snippets)
    user = f"USER LANGUAGE: {language}\n\nREFERENCE NOTES:\n{ctx}\n\nFAN QUESTION:\n{query}"
    online = await _try_online(api_key, model, SYSTEM_FAN, user, used)
    if online is not None:
        return online
    return Reply(
        text=_format_offline_fan(query, snippets),
        source="offline",
        model=None,
        used_ids=used,
    )


async def ops_reply(
    question: str,
    snippets: list[Snippet],
    snapshot_json: str,
    api_key: str | None,
    model: str = DEFAULT_MODEL,
    language: str = "en",
) -> Reply:
    used = [s.id for s in snippets]
    ctx = build_context(snippets)
    user = (
        f"USER LANGUAGE: {language}\n\n"
        f"LIVE SNAPSHOT:\n{snapshot_json}\n\n"
        f"REFERENCE NOTES:\n{ctx}\n\n"
        f"STAFF QUESTION:\n{question}"
    )
    online = await _try_online(api_key, model, SYSTEM_OPS, user, used)
    if online is not None:
        return online
    summary = snippets[0].title if snippets else "no reference notes matched"
    return Reply(
        text=_format_offline_ops(summary, snapshot_json),
        source="offline",
        model=None,
        used_ids=used,
    )


def _unaccent(text: str) -> str:
    """Strip diacritics so accented and unaccented queries match (cómo==como)."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


# Hint words per language; diacritics are folded at definition so accented
# and unaccented queries both match (cómo == como, estadio == estádio).
_LATIN_HINTS = {
    lang: {_unaccent(h) for h in hints}
    for lang, hints in {
        "es": {"cómo", "llego", "estadio", "transporte", "dónde", "gracias", "hola", "público"},
        "fr": {"comment", "stade", "transports", "où", "bonjour", "merci", "je"},
        "de": {"wie", "stadion", "öffentlich", "wo", "hallo", "danke", "ich"},
        "pt": {"como", "estádio", "transporte", "onde", "obrigado", "olá"},
        "it": {"come", "stadio", "trasporto", "dove", "grazie", "ciao"},
    }.items()
}
# ponytail: heuristic wordlist; wrong for short/ambiguous queries. Swap for a
# tiny langid model only if detection drives more than the language pill.


def detect_language(query: str) -> str:
    """Cheap script + wordlist hint. The LLM does the real translation.

    Non-Latin scripts map to one language each (high confidence). For Latin
    script we fall back to a small per-language wordlist before defaulting to
    English, so the detected-language pill is correct for common fan queries.
    """
    # Script detection runs on the raw string: NFKD would decompose Hangul
    # syllables into Jamo and drop them out of the codepoint ranges below.
    raw = query.strip()
    if not raw:
        return "en"
    for ch in raw:
        cp = ord(ch)
        if 0x3040 <= cp <= 0x30FF:  # hiragana / katakana
            return "ja"
        if 0xAC00 <= cp <= 0xD7AF:  # hangul
            return "ko"
        if 0x0600 <= cp <= 0x06FF:  # arabic
            return "ar"
        if 0x0400 <= cp <= 0x04FF:  # cyrillic
            return "ru"
    # Fold diacritics so accented/unaccented queries match (cómo == como), then
    # pick the language with the most hint-word hits. A single shared token
    # (e.g. English "come" vs Italian "come") is too weak, so we stay English
    # unless a language reaches >=2 hits; max-count breaks ES/PT ties.
    words = set(_WORD.findall(_unaccent(raw.lower())))
    best, best_n = "en", 1
    for lang, hints in _LATIN_HINTS.items():
        n = len(words & hints)
        if n > best_n:
            best, best_n = lang, n
    return best

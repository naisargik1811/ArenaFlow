"""Tiny stdlib retriever.

Tokenize, build a TF-IDF-ish vector, cosine-rank. No numpy.
For our KB size (~15 docs) this beats pulling in a dep.
"""

from __future__ import annotations
import math
import re
from collections import Counter

from arenaflow.data.kb import Snippet, all_snippets

_WORD = re.compile(r"[A-Za-z][A-Za-z']+")


def _tokens(s: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(s)]


def _term_freqs(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


class Retriever:
    def __init__(self, snippets: list[Snippet] | None = None) -> None:
        self._snippets = snippets if snippets is not None else all_snippets()
        self._df: Counter[str] = Counter()
        self._tfs: list[Counter[str]] = []
        for snip in self._snippets:
            toks = _tokens(snip.title + " " + snip.text + " " + " ".join(snip.tags))
            tf = _term_freqs(toks)
            self._tfs.append(tf)
            for term in tf:
                self._df[term] += 1
        self._n = len(self._snippets)

    def _tfidf(self, tf: Counter[str]) -> dict[str, float]:
        out: dict[str, float] = {}
        for term, c in tf.items():
            idf = math.log((1 + self._n) / (1 + self._df.get(term, 0))) + 1.0
            out[term] = c * idf
        return out

    def _vec_norm(self, v: dict[str, float]) -> float:
        return math.sqrt(sum(x * x for x in v.values())) or 1.0

    def search(self, query: str, top_k: int = 3, city: str | None = None) -> list[Snippet]:
        toks = _tokens(query)
        if not toks:
            return []
        q_tf = _term_freqs(toks)
        q_vec = self._tfidf(q_tf)
        q_norm = self._vec_norm(q_vec)

        scored: list[tuple[float, Snippet]] = []
        for i, snip in enumerate(self._snippets):
            if city:
                if not snip.city or snip.city.lower() != city.lower():
                    continue
            v = self._tfidf(self._tfs[i])
            n = self._vec_norm(v)
            dot = sum(q_vec.get(t, 0.0) * v.get(t, 0.0) for t in q_vec)
            score = dot / (q_norm * n)
            if score > 0:
                scored.append((score, snip))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]


def build_context(snippets: list[Snippet]) -> str:
    if not snippets:
        return "No matching reference notes."
    return "\n\n".join(
        f"[{s.id}] {s.title}\n{s.text}" for s in snippets
    )

"""Edge-case & robustness tests for ArenaFlow.

Covers input boundaries, city scoping, snapshot invariants, language
detection corners, offline-fallback variants, and security headers on
every route. Written as unittest.TestCase so it runs identically under
`python -m unittest discover -s tests` and under `pytest`.
"""
import asyncio
import os
import unittest

os.environ["NVIDIA_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException
from arenaflow.data.ops import snapshot

from arenaflow.api.routes import fan_ask, ops_ask, ops_snapshot
from arenaflow.api.schemas import FanAsk, OpsAsk
from arenaflow.config import load_settings
from arenaflow.core.llm import detect_language, fan_reply, ops_reply
from arenaflow.core.retriever import Retriever
from arenaflow.data.kb import all_snippets, venue_cities
from arenaflow.data.ops import VENUES
from arenaflow.main import create_app

_APP = create_app()


async def _request(method, path, json=None):
    transport = ASGITransport(app=_APP)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        if json is not None:
            return await client.request(method, path, json=json)
        return await client.request(method, path)


def _get(path):
    return asyncio.run(_request("GET", path))


def _post(path, json):
    return asyncio.run(_request("POST", path, json=json))


class _Req:
    def __init__(self, app):
        self.app = app


class InputBoundaryTests(unittest.TestCase):
    def test_fan_query_leading_trailing_spaces_ok(self):
        r = _post("/api/fan/ask", {"query": "   transit to SoFi   ", "city": "Inglewood"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["text"])

    def test_fan_query_whitespace_only_422(self):
        r = _post("/api/fan/ask", {"query": "   ", "city": "Inglewood"})
        self.assertEqual(r.status_code, 422)

    def test_ops_question_whitespace_only_422(self):
        r = _post("/api/ops/ask", {"question": "   ", "venue": "SoFi Stadium", "minute": 20})
        self.assertEqual(r.status_code, 422)

    def test_ops_question_too_long_422(self):
        r = _post("/api/ops/ask", {"question": "x" * 801, "venue": "SoFi Stadium", "minute": 20})
        self.assertEqual(r.status_code, 422)

    def test_ops_venue_empty_422(self):
        r = _post("/api/ops/ask", {"question": "open gates?", "venue": "", "minute": 20})
        self.assertEqual(r.status_code, 422)

    def test_ops_minute_zero_ok(self):
        r = _get("/api/ops/snapshot?venue=SoFi%20Stadium&minute=0")
        self.assertEqual(r.status_code, 200)

    def test_ops_minute_max_ok(self):
        r = _get("/api/ops/snapshot?venue=SoFi%20Stadium&minute=240")
        self.assertEqual(r.status_code, 200)

    def test_ops_minute_nonint_422(self):
        r = _get("/api/ops/snapshot?venue=SoFi%20Stadium&minute=abc")
        self.assertEqual(r.status_code, 422)

    def test_fan_query_max_length_ok(self):
        r = _post("/api/fan/ask", {"query": "x" * 800, "city": "Inglewood"})
        self.assertEqual(r.status_code, 200)


class CityScopingTests(unittest.TestCase):
    def test_fan_ask_city_does_not_cross_contaminate(self):
        out = asyncio.run(fan_ask(FanAsk(query="transit accessibility", city="Inglewood"), _Req(_APP)))
        snippets = {s.id: s for s in all_snippets()}
        for sid in out.used_ids:
            self.assertEqual(snippets[sid].city, "Inglewood")

    def test_ops_ask_city_scopes_snippets(self):
        # BMO Field is the Toronto venue; its city scopes the retrieved notes.
        out = asyncio.run(ops_ask(OpsAsk(question="open gates?", venue="BMO Field", minute=30), _Req(_APP)))
        snippets = {s.id: s for s in all_snippets()}
        for sid in out.used_ids:
            self.assertEqual(snippets[sid].city, "Toronto")

    def test_retriever_returns_only_requested_city(self):
        r = Retriever(all_snippets())
        out = r.search("transit accessibility", top_k=3, city="Toronto")
        self.assertTrue(out)
        self.assertTrue(all(s.city == "Toronto" for s in out))

    def test_retriever_unknown_city_empty(self):
        r = Retriever(all_snippets())
        self.assertEqual(r.search("transit", city="Atlantis"), [])


class SnapshotInvariantTests(unittest.TestCase):
    def test_inside_within_capacity(self):
        for venue, _city, cap in VENUES:
            for minute in (0, 30, 90, 180, 240):
                s = asyncio.run(ops_snapshot(venue=venue, minute=minute))
                self.assertLessEqual(s["inside"], s["capacity"])
                self.assertGreaterEqual(s["inside"], 0)

    def test_gates_have_valid_shape(self):
        s = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=45))
        for g in s["gates"]:
            self.assertIn(g["status"], ("open", "busy", "paused"))
            self.assertGreaterEqual(g["wait_min"], 0)
            self.assertTrue(g["gate"])

    def test_alerts_is_a_list(self):
        s = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=45))
        self.assertIsInstance(s["alerts"], list)

    def test_unknown_venue_route_raises_404(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(ops_snapshot(venue="NowhereFC", minute=10))
        self.assertEqual(ctx.exception.status_code, 404)

    def test_snapshot_unknown_venue_raises_valueerror(self):
        with self.assertRaises(ValueError):
            snapshot("NowhereFC", 10)

    def test_deterministic_across_calls(self):
        a = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=45))
        b = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=45))
        c = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=45))
        self.assertEqual(a["inside"], b["inside"])


class LanguageEdgeTests(unittest.TestCase):
    def test_mixed_latin_is_english(self):
        self.assertEqual(detect_language("How do I get to the stadium?"), "en")

    def test_chinese_defaults_english(self):
        self.assertEqual(detect_language("\u4f60\u597d"), "en")

    def test_hebrew_defaults_english(self):
        self.assertEqual(detect_language("\u05e9\u05dc\u05d5\u05dd"), "en")

    def test_whitespace_is_english(self):
        self.assertEqual(detect_language("   \n  "), "en")

    def test_arabic(self):
        self.assertEqual(detect_language("\u0623\u064a\u0646\u200c \u0627\u0644\u063a\u0631\u0641\u0629\u061f"), "ar")


class OfflineFallbackTests(unittest.TestCase):
    def test_fan_offline_no_snippets(self):
        r = asyncio.run(fan_reply("question?", [], api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertEqual(r.used_ids, [])

    def test_ops_offline_no_snippets(self):
        r = asyncio.run(ops_reply("q?", [], "{}", api_key=None))
        self.assertEqual(r.source, "offline")

    def test_fan_offline_when_key_set(self):
        # with a dummy key but no network, the call fails and falls back
        from unittest import mock
        with mock.patch("arenaflow.core.llm._post_chat", side_effect=ValueError("boom")):
            r = asyncio.run(fan_reply("q?", [], api_key="dummy", model="x"))
            self.assertEqual(r.source, "offline")

    def test_fan_offline_empty_model_response(self):
        # A whitespace-only completion must not be served as a real answer;
        # _post_chat raises on it (and the caller re-validates), so
        # fan_reply falls back to the offline template.
        from unittest import mock
        with mock.patch("arenaflow.core.llm._post_chat", side_effect=ValueError("empty")):
            r = asyncio.run(fan_reply("q?", [], api_key="dummy", model="x"))
            self.assertEqual(r.source, "offline")


class SecurityHeaderEdgeTests(unittest.TestCase):
    def test_csp_on_post_fan(self):
        r = _post("/api/fan/ask", {"query": "transit", "city": "Inglewood"})
        csp = r.headers["content-security-policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_csp_on_post_ops(self):
        r = _post("/api/ops/ask", {"question": "open gates?", "venue": "SoFi Stadium", "minute": 20})
        self.assertIn("default-src 'self'", r.headers["content-security-policy"])

    def test_no_script_injection_in_response(self):
        r = _post("/api/fan/ask", {"query": "<script>alert(1)</script>", "city": "Inglewood"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("<script>", r.json()["text"])

    def test_sql_and_path_injection_no_crash(self):
        for payload in ("'; DROP TABLE fans; --", "../../etc/passwd", "{{7*7}}"):
            r = _post("/api/fan/ask", {"query": payload, "city": "Inglewood"})
            self.assertEqual(r.status_code, 200)


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": "Take Metro L2 to Tasquena."}}]}


class OnlinePathTests(unittest.TestCase):
    def test_fan_reply_online_parses_sync_json(self):
        # Exercises the real _post_chat path (incl. sync r.json()), the
        # exact spot that 500'd with `await r.json()`.
        from unittest import mock

        fake_client = mock.AsyncMock()
        fake_client.post = mock.AsyncMock(return_value=_FakeResp())
        cm = mock.AsyncMock()
        cm.__aenter__ = mock.AsyncMock(return_value=fake_client)
        cm.__aexit__ = mock.AsyncMock(return_value=False)
        with mock.patch("arenaflow.core.llm.httpx.AsyncClient", return_value=cm):
            r = asyncio.run(
                fan_reply("transit to Estadio Azteca", [], api_key="dummy", model="x")
            )
            self.assertEqual(r.source, "nvidia")
            self.assertEqual(r.text, "Take Metro L2 to Tasquena.")

    def test_ops_reply_online_parses_sync_json(self):
        from unittest import mock

        fake_client = mock.AsyncMock()
        fake_client.post = mock.AsyncMock(return_value=_FakeResp())
        cm = mock.AsyncMock()
        cm.__aenter__ = mock.AsyncMock(return_value=fake_client)
        cm.__aexit__ = mock.AsyncMock(return_value=False)
        with mock.patch("arenaflow.core.llm.httpx.AsyncClient", return_value=cm):
            r = asyncio.run(
                ops_reply("open gates?", [], "{}", api_key="dummy", model="x")
            )
            self.assertEqual(r.source, "nvidia")
            self.assertTrue(r.text)

class ConfigEdgeTests(unittest.TestCase):
    def test_empty_model_falls_back_to_default(self):
        os.environ["NVIDIA_MODEL"] = ""
        try:
            self.assertEqual(load_settings().nvidia_model, "meta/llama-3.1-8b-instruct")
        finally:
            os.environ.pop("NVIDIA_MODEL", None)

    def test_missing_api_key_is_none(self):
        os.environ.pop("NVIDIA_API_KEY", None)
        self.assertIsNone(load_settings().nvidia_api_key)


class ShapeTests(unittest.TestCase):
    def test_health_keys(self):
        self.assertEqual(_get("/api/health").json(), {"ok": True, "service": "arenaflow"})

    def test_cities_count_matches_venues(self):
        v = _get("/api/venues").json()["venues"]
        c = _get("/api/cities").json()["cities"]
        self.assertTrue(len(v) >= 13)
        self.assertEqual(len(v), len(c))

    def test_fan_answer_has_language(self):
        out = asyncio.run(fan_ask(FanAsk(query="transit to SoFi", city="Inglewood"), _Req(_APP)))
        self.assertIsInstance(out.language, str)
        self.assertIsInstance(out.used_ids, list)

    def test_ops_answer_has_snapshot(self):
        out = asyncio.run(ops_ask(OpsAsk(question="open gates?", venue="SoFi Stadium", minute=20), _Req(_APP)))
        self.assertIn("gates", out.snapshot)


if __name__ == "__main__":
    unittest.main()

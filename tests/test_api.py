import os
import asyncio
import unittest

os.environ["OPENAI_API_KEY"] = ""
os.environ["NVIDIA_API_KEY"] = ""  # force offline path

from arenaflow.api.routes import fan_ask, ops_ask, ops_snapshot
from arenaflow.api.schemas import FanAsk, OpsAsk
from arenaflow.main import create_app


class _Req:
    """Minimal stand-in for a FastAPI request: exposes .app.state."""
    def __init__(self, app):
        self.app = app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.req = _Req(cls.app)

    def test_venues(self) -> None:
        names = self.app.state  # not used directly here; route reads from KB
        from arenaflow.data.ops import venue_names
        v = venue_names()
        self.assertIn("SoFi Stadium", v)
        self.assertIn("Estadio Azteca", v)

    def test_fan_ask(self) -> None:
        body = FanAsk(query="transit to SoFi Stadium")
        out = asyncio.run(fan_ask(body, self.req))
        self.assertIn(out.source, ("nvidia", "offline"))
        self.assertTrue(out.text)

    def test_fan_ask_validates(self) -> None:
        # Pydantic validation - try empty
        with self.assertRaises(Exception):
            FanAsk(query="")

    def test_ops_snapshot(self) -> None:
        s = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=30))
        self.assertEqual(s["venue"], "SoFi Stadium")
        self.assertGreater(s["capacity"], 0)

    def test_ops_ask(self) -> None:
        body = OpsAsk(question="should we open more gates?", venue="SoFi Stadium", minute=20)
        out = asyncio.run(ops_ask(body, self.req))
        self.assertIn(out.source, ("nvidia", "offline"))
        self.assertIn("snapshot", out.model_dump())
        self.assertIsInstance(out.language, str)




class FanAnswerShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.req = _Req(cls.app)

    def test_fan_answer_required_fields(self) -> None:
        out = asyncio.run(fan_ask(FanAsk(query="transit to SoFi Stadium", city="Inglewood"), self.req))
        self.assertIn(out.source, ("nvidia", "offline"))
        self.assertIsInstance(out.used_ids, list)
        self.assertTrue(out.text)
        self.assertIsInstance(out.language, str)

    def test_fan_city_no_match_is_offline(self) -> None:
        out = asyncio.run(fan_ask(FanAsk(query="transit", city="Atlantis"), self.req))
        self.assertEqual(out.source, "offline")
        self.assertEqual(out.used_ids, [])

    def test_ops_snapshot_keys(self) -> None:
        s = asyncio.run(ops_snapshot(venue="SoFi Stadium", minute=30))
        for k in ("venue", "gates", "inside", "capacity", "weather", "air_quality"):
            self.assertIn(k, s)


if __name__ == "__main__":
    unittest.main()

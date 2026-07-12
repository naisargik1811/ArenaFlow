import asyncio
import unittest
from unittest import mock

from arenaflow.core.llm import detect_language, fan_reply, ops_reply
from arenaflow.core.retriever import Retriever
from arenaflow.data.kb import all_snippets


class LangTests(unittest.TestCase):
    def test_english(self) -> None:
        self.assertEqual(detect_language("Where is the sensory room?"), "en")

    def test_arabic(self) -> None:
        self.assertEqual(detect_language("أين الغرفة الحسية؟"), "ar")

    def test_japanese(self) -> None:
        self.assertEqual(detect_language("会場へのアクセスは？"), "ja")

    def test_latin_defaults_to_en(self) -> None:
        self.assertEqual(detect_language("¿Cómo llego al estadio?"), "en")

    def test_empty(self) -> None:
        self.assertEqual(detect_language(""), "en")


class FallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snips = Retriever(all_snippets()).search("SoFi Stadium transit", top_k=2)

    def test_fan_offline(self) -> None:
        r = asyncio.run(fan_reply("How do I get to SoFi Stadium?", self.snips, api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertTrue(r.text)
        self.assertIn(r.used_ids[0], [s.id for s in self.snips])

    def test_ops_offline(self) -> None:
        r = asyncio.run(ops_reply("Where to redirect?", self.snips, '{"inside": 1000}', api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertIn("Situation", r.text)




class LangEdgeTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(detect_language(""), "en")
    def test_whitespace(self) -> None:
        self.assertEqual(detect_language("   "), "en")
    def test_japanese(self) -> None:
        self.assertEqual(detect_language("会場へのアクセスは？"), "ja")
    def test_korean(self) -> None:
        self.assertEqual(detect_language("경기장 가는길"), "ko")
    def test_arabic(self) -> None:
        self.assertEqual(detect_language("أين الغرفة الحسية؟"), "ar")
    def test_cyrillic(self) -> None:
        self.assertEqual(detect_language("Где сенсорная комната?"), "ru")
    def test_latin_defaults_en(self) -> None:
        self.assertEqual(detect_language("Where is the sensory room?"), "en")

class NetworkFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snips = Retriever(all_snippets()).search("SoFi transit", city="Inglewood")

    @mock.patch("arenaflow.core.llm._post_chat", side_effect=ValueError("boom"))
    def test_fan_offline_on_error(self, _m) -> None:
        r = asyncio.run(fan_reply("q", self.snips, api_key="dummy", model="x"))
        self.assertEqual(r.source, "offline")

    @mock.patch("arenaflow.core.llm._post_chat", side_effect=ValueError("boom"))
    def test_ops_offline_on_error(self, _m) -> None:
        r = asyncio.run(ops_reply("q", self.snips, "{}", api_key="dummy", model="x"))
        self.assertEqual(r.source, "offline")

    def test_offline_with_no_snippets(self) -> None:
        r = asyncio.run(fan_reply("q", [], api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertEqual(r.used_ids, [])


if __name__ == "__main__":
    unittest.main()

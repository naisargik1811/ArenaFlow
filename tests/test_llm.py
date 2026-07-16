import asyncio
import unittest
from unittest import mock

from arenaflow.core.llm import detect_language, fan_reply, ops_reply
from arenaflow.core.retriever import Retriever, _WORD
from arenaflow.data.kb import Snippet, all_snippets


class LangTests(unittest.TestCase):
    def test_english(self) -> None:
        self.assertEqual(detect_language("Where is the sensory room?"), "en")

    def test_spanish_detected(self) -> None:
        self.assertEqual(detect_language("¿Cómo llego al estadio?"), "es")

    def test_french_detected(self) -> None:
        self.assertEqual(detect_language("Comment aller au stade?"), "fr")

    def test_german_detected(self) -> None:
        self.assertEqual(detect_language("Wie komme ich zum stadion?"), "de")

    def test_portuguese_detected(self) -> None:
        # Includes a PT-only cue ("onde") so it beats the ES/PT "como"+"estadio" tie.
        self.assertEqual(detect_language("Como chegar ao estadio? Onde fica?"), "pt")

    def test_italian_detected(self) -> None:
        self.assertEqual(detect_language("Come arrivare allo stadio?"), "it")

    def test_accented_spanish_detected(self) -> None:
        # Accented hint words must survive tokenisation (regression guard for
        # the _WORD regex dropping accented letters).
        self.assertEqual(detect_language("¿Dónde está el estadio?"), "es")

    def test_english_not_mislabeled(self) -> None:
        # English "come" must not collide with Italian "come" (>=2-hint rule).
        self.assertEqual(detect_language("How do I come to the stadium?"), "en")

    def test_single_hint_word_is_not_enough(self) -> None:
        # Exactly one matching hint word (e.g. lone "stadio") stays English.
        self.assertEqual(detect_language("stadio"), "en")

    def test_latin_defaults_to_en(self) -> None:
        self.assertEqual(detect_language("Where is the sensory room?"), "en")


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


class RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ret = Retriever(all_snippets())

    def test_normal_scoring_ranks_city(self) -> None:
        # Token overlap should rank the matching venue first.
        hits = self.ret.search("metro station gate")
        self.assertTrue(hits)
        self.assertEqual(hits[0].city, "Mexico City")

    def test_city_filter_excludes_other_cities(self) -> None:
        hits = self.ret.search("stadium gate", city="Houston")
        self.assertTrue(hits)
        self.assertTrue(all(h.city == "Houston" for h in hits))

    def test_no_tokens_returns_empty(self) -> None:
        # Non-Latin query has no ASCII tokens -> no retrieval.
        self.assertEqual(self.ret.search("スタジアムへの行き方"), [])

    def test_no_city_and_no_overlap_returns_empty(self) -> None:
        self.assertEqual(self.ret.search("kangaroo telescope penguin"), [])

    def test_city_fallback_when_no_token_overlap(self) -> None:
        # Query shares no tokens with the KB, so normal scoring yields nothing;
        # with a city selected it must still return that city's snippet.
        hits = self.ret.search("kangaroo telescope penguin", city="Mexico City")
        self.assertTrue(hits, "city-scoped fallback should return the venue snippet")
        self.assertTrue(all(h.city == "Mexico City" for h in hits))

    def test_city_fallback_respects_top_k(self) -> None:
        # Build a retriever with several same-city snippets to exercise the
        # city_snips[:top_k] slice in the fallback branch.
        snips = [
            Snippet(f"mc-{i}", f"Venue {i} (Mexico City)", "transport access", ("venue",), "Mexico City")
            for i in range(4)
        ]
        ret = Retriever(snips)
        hits = ret.search("kangaroo telescope penguin", top_k=2, city="Mexico City")
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(h.city == "Mexico City" for h in hits))

    def test_top_k_caps_normal_scoring(self) -> None:
        hits = self.ret.search("gate access stadium", top_k=1)
        self.assertEqual(len(hits), 1)


class ReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snips = Retriever(all_snippets()).search("SoFi transit", city="Inglewood")

    def test_fan_offline_without_key(self) -> None:
        r = asyncio.run(fan_reply("Where is the sensory room?", self.snips, api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertIsNone(r.model)
        self.assertTrue(r.used_ids)

    def test_ops_offline_without_key(self) -> None:
        r = asyncio.run(ops_reply("Where to redirect?", self.snips, '{"inside": 1000}', api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertIn("Situation", r.text)

    def test_offline_with_no_snippets(self) -> None:
        r = asyncio.run(fan_reply("q", [], api_key=None))
        self.assertEqual(r.source, "offline")
        self.assertEqual(r.used_ids, [])


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


class TokenizerTests(unittest.TestCase):
    def test_accented_words_kept_intact(self) -> None:
        self.assertEqual(_WORD.findall("¿Cómo llego al estadio?".lower()), ["cómo", "llego", "al", "estadio"])

    def test_ascii_only_still_works(self) -> None:
        self.assertEqual(_WORD.findall("Where is the gate?"), ["Where", "is", "the", "gate"])


if __name__ == "__main__":
    unittest.main()

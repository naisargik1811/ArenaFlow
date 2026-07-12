import unittest

from arenaflow.core.retriever import Retriever
from arenaflow.data.kb import all_snippets


class RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.r = Retriever(all_snippets())

    def test_empty_query_returns_empty(self) -> None:
        self.assertEqual(self.r.search(""), [])

    def test_venue_match(self) -> None:
        out = self.r.search("How do I get to SoFi Stadium by transit?")
        ids = [s.id for s in out]
        self.assertTrue("SoFi" in (out[0].title if out else ""), ids)

    def test_city_filter(self) -> None:
        out = self.r.search("transit accessibility Toronto BMO Field", city="Toronto")
        for s in out:
            self.assertEqual(s.city, "Toronto")

    def test_no_match(self) -> None:
        out = self.r.search("klingon bathtubs", top_k=3)
        self.assertEqual(out, [])




class RetrieverEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.r = Retriever(all_snippets())

    def test_city_no_match(self) -> None:
        self.assertEqual(self.r.search("transit", city="Atlantis"), [])

    def test_city_case_insensitive(self) -> None:
        out = self.r.search("transit", city="inglewood")
        self.assertTrue(all(s.city == "Inglewood" for s in out), [s.city for s in out])

    def test_top_k_limit(self) -> None:
        out = self.r.search("stadium transit accessibility", top_k=2, city="Inglewood")
        self.assertLessEqual(len(out), 2)

    def test_unicode_query(self) -> None:
        out = self.r.search("会場へのアクセスは？")
        self.assertIsInstance(out, list)

    def test_none_city_returns_all(self) -> None:
        out = self.r.search("sustainability")
        self.assertIsInstance(out, list)


if __name__ == "__main__":
    unittest.main()

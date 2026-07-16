import os
import unittest
import httpx
from unittest import mock

from arenaflow.data import ops

class TransitSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure the live feed is disabled so the synthetic source is used.
        self._prev = os.environ.pop("ARENAFLOW_LIVE_TRANSIT_URL", None)

    def tearDown(self) -> None:
        # Always clear the var so later tests stay on the synthetic source.
        os.environ.pop("ARENAFLOW_LIVE_TRANSIT_URL", None)
        if self._prev is not None:
            os.environ["ARENAFLOW_LIVE_TRANSIT_URL"] = self._prev

    def test_synthetic_by_default(self) -> None:
        # No live URL configured -> deterministic synthetic transit data.
        self.assertEqual(ops.transit_status("SoFi Stadium"), ops.TRANSIT["SoFi Stadium"])

    def test_sustainability_accessor(self) -> None:
        self.assertEqual(ops.sustainability_for("SoFi Stadium"), ops.SUSTAIN["SoFi Stadium"])

    def test_live_feed_used_when_configured(self) -> None:
        feed = {"SoFi Stadium": {"SoFi Shuttle": "Delayed", "LAX FlyAway": "On time"}}
        os.environ["ARENAFLOW_LIVE_TRANSIT_URL"] = "http://feed.example/transit"
        with mock.patch("arenaflow.data.ops.httpx.Client") as client:
            client.return_value.__enter__.return_value.get.return_value.json.return_value = feed
            client.return_value.__enter__.return_value.get.return_value.raise_for_status.return_value = None
            self.assertEqual(ops.transit_status("SoFi Stadium"), feed["SoFi Stadium"])

    def test_fallback_to_synthetic_on_error(self) -> None:
        os.environ["ARENAFLOW_LIVE_TRANSIT_URL"] = "http://feed.example/transit"
        with mock.patch("arenaflow.data.ops.httpx.Client") as client:
            client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("boom")
            # Must not raise; falls back to the synthetic source.
            self.assertEqual(ops.transit_status("SoFi Stadium"), ops.TRANSIT["SoFi Stadium"])


if __name__ == "__main__":
    unittest.main()

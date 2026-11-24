"""W1 離線測試：不得把示範資料當成官方即時觀測。"""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from airguard.moenv import (DataError, FetchError, MOENVClient, parse_aqi,
                           parse_hourly_pm25, quality_summary)

BASE = Path(__file__).resolve().parents[1] / "data" / "fixtures"


class MOENVTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((BASE / name).read_text(encoding="utf-8"))

    def test_hourly_width_to_long_24_slots(self):
        rows = parse_hourly_pm25(self.fixture("aqx_p_13_synthetic.json"))
        self.assertEqual(len(rows), 24)
        self.assertEqual(rows[0]["observed_at_utc"], "2026-11-22T16:00:00+00:00")
        self.assertEqual(rows[0]["value_ug_m3"], 12.5)
        self.assertEqual(rows[1]["quality_flag"], "missing")
        self.assertIsNone(rows[1]["value_ug_m3"])
        self.assertEqual(rows[3]["quality_flag"], "invalid")
        self.assertEqual(quality_summary(rows), {"slots": 24, "ok": 2, "missing": 21, "invalid": 1, "valid_ratio": 2/24})

    def test_hourly_rejects_non_mass_units(self):
        payload = self.fixture("aqx_p_13_synthetic.json")
        payload["records"][0]["ItemUnit"] = "ppb"
        with self.assertRaises(DataError):
            parse_hourly_pm25(payload)

    def test_hourly_rejects_duplicate_station_time(self):
        payload = self.fixture("aqx_p_13_synthetic.json")
        payload["records"].append(dict(payload["records"][0]))
        with self.assertRaises(DataError):
            parse_hourly_pm25(payload)

    def test_bad_json_schema_rejected(self):
        with self.assertRaises(DataError):
            parse_hourly_pm25({"records": "not-array"})

    def test_aqi_official_not_pm25(self):
        rows = parse_aqi(self.fixture("aqx_p_432_synthetic.json"), fetched_at=datetime(2026, 11, 24, tzinfo=timezone.utc))
        self.assertEqual(rows[0]["official_aqi"], 42)
        self.assertEqual(rows[0]["observed_pm25_ug_m3"], 12.1)
        self.assertEqual(rows[0]["published_at_utc"], "2026-11-23T02:00:00+00:00")
        self.assertEqual(rows[0]["retrieved_at_utc"], "2026-11-24T00:00:00+00:00")

    def test_aqi_unknown_publication_is_not_fetched_time(self):
        payload = self.fixture("aqx_p_432_synthetic.json")
        payload["records"][0].pop("publishtime")
        self.assertIsNone(parse_aqi(payload)[0]["published_at_utc"])

    def test_api_requires_key_and_does_not_log_key(self):
        with patch.dict("os.environ", {"MOENV_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "MOENV_API_KEY"):
                MOENVClient()
        client = MOENVClient("top-secret-key")
        with patch("airguard.moenv.urlopen", side_effect=OSError("top-secret-key authorization failed")):
            with self.assertRaises(FetchError) as ctx:
                client.fetch("AQX_P_13")
        self.assertNotIn("top-secret-key", str(ctx.exception))

    def test_disallow_unknown_dataset_and_bad_page(self):
        client = MOENVClient("test")
        with self.assertRaises(ValueError):
            client.fetch("AQX_P_999")
        with self.assertRaises(ValueError):
            client.fetch("AQX_P_13", limit=0)


if __name__ == "__main__":
    unittest.main()

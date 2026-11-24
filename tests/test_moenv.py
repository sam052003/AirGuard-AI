"""W1 離線測試：不得把示範資料當成官方即時觀測。"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from airguard.__main__ import main as cli_main
from airguard.moenv import (
    DataError,
    FetchError,
    MOENVClient,
    parse_aqi,
    parse_historical_aqi,
    parse_hourly_pm25,
    parse_stations,
    quality_summary,
    resolve_api_key,
    station_month_quality_report,
)

BASE = Path(__file__).resolve().parents[1] / "data" / "fixtures"


class _FakeHTTPResponse:
    def __init__(self, payload):
        self._raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


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

    def test_dotenv_loading_and_system_env_precedence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("MOENV_API_KEY=fake-dotenv-key-001\n", encoding="utf-8")

            # 1) 系統環境變數未設定時，從指定的假 .env 讀取（不讀使用者真實 .env）
            resolved = resolve_api_key(env={}, env_file=env_path)
            self.assertEqual(resolved, "fake-dotenv-key-001")

            # 2) 已存在系統環境變數時，優先使用系統環境變數
            resolved_sys = resolve_api_key(
                env={"MOENV_API_KEY": "fake-system-key-002"},
                env_file=env_path,
            )
            self.assertEqual(resolved_sys, "fake-system-key-002")

            # 3) .env 不存在或缺少金鑰時清楚提示如何設定，且不洩露任何金鑰
            missing_path = Path(tmpdir) / "nonexistent.env"
            with self.assertRaisesRegex(ValueError, r"\.env"):
                resolve_api_key(env={}, env_file=missing_path)

            empty_env_path = Path(tmpdir) / "empty.env"
            empty_env_path.write_text("MOENV_API_KEY=\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                err_buf = io.StringIO()
                with redirect_stderr(err_buf):
                    code = cli_main(["--dataset", "AQX_P_432", "--live", "--env-file", str(empty_env_path)])
                self.assertEqual(code, 1)
                self.assertIn("MOENV_API_KEY", err_buf.getvalue())
                self.assertNotIn("fake-dotenv-key-001", err_buf.getvalue())

    def test_parse_stations_taichung_and_coordinates(self):
        payload = self.fixture("aqx_p_07_synthetic.json")
        fetched = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        taichung = parse_stations(payload, county="臺中市", fetched_at=fetched)
        self.assertEqual([s["station_id"] for s in taichung], ["991", "992"])
        self.assertEqual(taichung[0]["longitude_twd97"], 120.616917)
        self.assertEqual(taichung[0]["latitude_twd97"], 24.162197)
        self.assertEqual(taichung[0]["coordinate_system"], "TWD97")
        self.assertEqual(taichung[0]["coordinate_status"], "ok")
        self.assertIsNone(taichung[1]["longitude_twd97"])
        self.assertIsNone(taichung[1]["latitude_twd97"])
        self.assertEqual(taichung[1]["coordinate_status"], "missing")

        bad_coord = self.fixture("aqx_p_07_synthetic.json")
        bad_coord["records"][0]["twd97lon"] = "180.0"
        with self.assertRaises(DataError):
            parse_stations(bad_coord)

    def test_parse_historical_aqi_separates_aqi_and_pm25_windows(self):
        payload = self.fixture("aqx_p_488_synthetic.json")
        rows = parse_historical_aqi(payload, fetched_at=datetime(2026, 11, 24, tzinfo=timezone.utc))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_id"], "AQX_P_488")
        self.assertEqual(rows[0]["official_aqi"], 55)
        self.assertEqual(rows[0]["observed_pm25_ug_m3"], 14.0)
        self.assertEqual(rows[0]["pm25_moving_avg_ug_m3"], 16.5)
        self.assertEqual(rows[0]["observed_at_utc"], "2026-11-23T06:00:00+00:00")
        self.assertIsNone(rows[0]["published_at_utc"])

    def test_hourly_duplicate_policies_and_outliers(self):
        payload = self.fixture("aqx_p_13_synthetic.json")
        payload["records"][0]["MonitorDate"] = "2026-11-23 "
        payload["records"][0]["MonitorValue05"] = "1500"
        payload["records"].append(dict(payload["records"][0]))

        dup_log = []
        rows = parse_hourly_pm25(payload, on_duplicate="dedup_identical", duplicate_log=dup_log)
        self.assertEqual(len(rows), 24)
        self.assertEqual(len(dup_log), 24)
        self.assertEqual(rows[5]["quality_flag"], "invalid")
        self.assertIsNone(rows[5]["value_ug_m3"])

        # 同站同時刻若數值衝突，dedup_identical 仍必須拋出 DataError
        conflicting = self.fixture("aqx_p_13_synthetic.json")
        duplicate_row = dict(conflicting["records"][0])
        duplicate_row["MonitorValue00"] = "99.0"
        conflicting["records"].append(duplicate_row)
        with self.assertRaises(DataError):
            parse_hourly_pm25(conflicting, on_duplicate="dedup_identical")

        # flag_conflict 策略將衝突時槽標記為 invalid 且不靜默選最後一筆
        conflict_log = []
        flagged_rows = parse_hourly_pm25(conflicting, on_duplicate="flag_conflict", duplicate_log=conflict_log)
        self.assertIsNone(flagged_rows[0]["value_ug_m3"])
        self.assertEqual(flagged_rows[0]["quality_flag"], "invalid")
        self.assertTrue(any(e["resolution"] == "conflict_flagged_invalid" for e in conflict_log))

    def test_station_month_quality_report_and_horizon_pairs(self):
        record = {
            "SiteId": "999",
            "SiteName": "示例測站（合成資料）",
            "ItemEngName": "PM2.5",
            "ItemName": "細懸浮微粒",
            "ItemUnit": "μg/m3",
            "MonitorDate": "2026-11-23 ",
        }
        for hour in range(24):
            record[f"MonitorValue{hour:02d}"] = str(10 + hour) if hour not in (7, 8) else "--"
        rows = parse_hourly_pm25([record])
        report = station_month_quality_report(rows)
        self.assertEqual(report["backtest_mode"], "reconstructed_from_observed_at")
        self.assertEqual(len(report["station_months"]), 1)
        m = report["station_months"][0]
        self.assertEqual(m["year_month_local"], "2026-11")
        self.assertEqual(m["expected_hours"], 720)
        self.assertEqual(m["window_expected_hours"], 24)
        self.assertEqual(m["actual_slots"], 24)
        self.assertEqual(m["valid_hours"], 22)
        self.assertEqual(m["missing_hours"], 2)
        self.assertEqual(m["max_consecutive_missing_hours"], 2)
        self.assertEqual(m["horizon_valid_pairs"], {"1h": 20, "3h": 17, "6h": 14})

    def test_paginated_fetch_provenance_and_sha256_without_leaking_key(self):
        page1 = [{"SiteId": "999", "SiteName": "合成站", "ItemEngName": "PM2.5", "ItemName": "細懸浮微粒", "ItemUnit": "μg/m3", "MonitorDate": "2026-11-23"}]
        page2 = []
        client = MOENVClient("fake-secret-key-999", load_dotenv_file=False)
        with patch("airguard.moenv.urlopen", side_effect=[_FakeHTTPResponse(page1), _FakeHTTPResponse(page2)]):
            batch = client.fetch_pages("AQX_P_13", limit=2, start_offset=0, max_pages=3, station_id="999", item_eng_name="PM2.5")
        self.assertEqual(len(batch["records"]), 1)
        prov = batch["provenance"]
        self.assertEqual(prov["source_id"], "AQX_P_13")
        self.assertEqual(prov["query_params_without_api_key"]["pages_fetched"], 1)
        self.assertEqual(len(prov["sha256"]), 64)
        self.assertNotIn("fake-secret-key-999", json.dumps(batch, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

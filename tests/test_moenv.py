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
    build_moenv_filters,
    load_raw_snapshot,
    parse_aqi,
    parse_historical_aqi,
    parse_hourly_pm25,
    parse_stations,
    quality_summary,
    resolve_api_key,
    station_month_quality_report,
    validate_moenv_filters,
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
                MOENVClient(load_dotenv_file=False)
        client = MOENVClient("top-secret-key", load_dotenv_file=False)
        with patch("airguard.moenv.urlopen", side_effect=OSError("top-secret-key authorization failed")):
            with self.assertRaises(FetchError) as ctx:
                client.fetch("AQX_P_13")
        self.assertNotIn("top-secret-key", str(ctx.exception))

    def test_disallow_unknown_dataset_and_bad_page(self):
        client = MOENVClient("test", load_dotenv_file=False)
        with self.assertRaises(ValueError):
            client.fetch("AQX_P_999")
        with self.assertRaises(ValueError):
            client.fetch("AQX_P_13", limit=0)

    def test_dotenv_loading_empty_env_fallback_and_system_env_precedence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("MOENV_API_KEY=fake-dotenv-key-001\n", encoding="utf-8")

            # 1) 系統環境變數未設定時，從指定的假 .env 讀取（不讀使用者真實 .env）
            resolved = resolve_api_key(env={}, env_file=env_path)
            self.assertEqual(resolved, "fake-dotenv-key-001")

            # 2) 系統環境變數存在但為空字串時，視為缺少並回退至 .env
            resolved_empty = resolve_api_key(env={"MOENV_API_KEY": "   "}, env_file=env_path)
            self.assertEqual(resolved_empty, "fake-dotenv-key-001")
            with patch.dict("os.environ", {"MOENV_API_KEY": ""}, clear=True):
                client_from_dotenv = MOENVClient(env_file=env_path)
                self.assertEqual(client_from_dotenv._key, "fake-dotenv-key-001")

            # 3) 已存在非空系統環境變數時，優先使用系統環境變數
            resolved_sys = resolve_api_key(
                env={"MOENV_API_KEY": "fake-system-key-002"},
                env_file=env_path,
            )
            self.assertEqual(resolved_sys, "fake-system-key-002")

            # 4) .env 不存在或缺少金鑰時清楚提示如何設定，且不洩露任何金鑰
            missing_path = Path(tmpdir) / "nonexistent.env"
            with self.assertRaisesRegex(ValueError, r"\.env"):
                resolve_api_key(env={"MOENV_API_KEY": ""}, env_file=missing_path)

            empty_env_path = Path(tmpdir) / "empty.env"
            empty_env_path.write_text("MOENV_API_KEY=\n", encoding="utf-8")
            with patch.dict("os.environ", {"MOENV_API_KEY": ""}, clear=True):
                err_buf = io.StringIO()
                with redirect_stderr(err_buf):
                    code = cli_main(["--dataset", "AQX_P_432", "--live", "--env-file", str(empty_env_path)])
                self.assertEqual(code, 1)
                self.assertIn("MOENV_API_KEY", err_buf.getvalue())
                self.assertNotIn("fake-dotenv-key-001", err_buf.getvalue())

    def test_strict_filter_validation_rejects_injection(self):
        self.assertEqual(
            build_moenv_filters(station_id="32", item_eng_name="PM2.5"),
            "siteid,EQ,32|itemengname,EQ,PM2.5",
        )
        for bad_station in ("32|itemengname,EQ,PM10", "32,EQ,1", "abc", "../32", "1234567"):
            with self.subTest(bad_station=bad_station):
                with self.assertRaises(ValueError):
                    build_moenv_filters(station_id=bad_station)
        for bad_item in ("PM2.5|siteid,EQ,1", "UNKNOWN_ITEM", "PM2.5,EQ,1"):
            with self.subTest(bad_item=bad_item):
                with self.assertRaises(ValueError):
                    build_moenv_filters(item_eng_name=bad_item)
        for bad_raw_filter in (
            "siteid,NE,32",
            "siteid,EQ,32|unknown,EQ,1",
            "siteid,EQ,32|itemengname,EQ,NOT_ALLOWED",
            "siteid,EQ,32,extra",
        ):
            with self.subTest(bad_raw_filter=bad_raw_filter):
                with self.assertRaises(ValueError):
                    validate_moenv_filters(bad_raw_filter)

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

        # 可配置的 max_valid_pm25_ug_m3 門檻
        rows_high_threshold = parse_hourly_pm25(
            payload, on_duplicate="dedup_identical", max_valid_pm25_ug_m3=2000.0
        )
        self.assertEqual(rows_high_threshold[5]["quality_flag"], "ok")
        self.assertEqual(rows_high_threshold[5]["value_ug_m3"], 1500.0)

        # 同站同時刻若數值衝突，dedup_identical 仍必須拋出 DataError
        conflicting = self.fixture("aqx_p_13_synthetic.json")
        duplicate_row = dict(conflicting["records"][0])
        duplicate_row["MonitorValue00"] = "99.0"
        conflicting["records"].append(duplicate_row)
        with self.assertRaises(DataError):
            parse_hourly_pm25(conflicting, on_duplicate="dedup_identical")

        # flag_conflict 策略：必須先記錄 previous_value_ug_m3=12.5 與 conflicting_value_ug_m3=99.0，再標記為 invalid
        conflict_log = []
        flagged_rows = parse_hourly_pm25(conflicting, on_duplicate="flag_conflict", duplicate_log=conflict_log)
        self.assertIsNone(flagged_rows[0]["value_ug_m3"])
        self.assertEqual(flagged_rows[0]["quality_flag"], "invalid")
        conflicts = [e for e in conflict_log if e["resolution"] == "conflict_flagged_invalid"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["previous_value_ug_m3"], 12.5)
        self.assertEqual(conflicts[0]["previous_quality_flag"], "ok")
        self.assertEqual(conflicts[0]["conflicting_value_ug_m3"], 99.0)
        self.assertEqual(conflicts[0]["conflicting_quality_flag"], "ok")

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
        report = station_month_quality_report(rows, min_trainable_hours=20)
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
        # 區分片段視窗可訓練 vs 整月日曆完整可訓練
        self.assertFalse(m["is_full_calendar_span"])
        self.assertFalse(m["is_calendar_month_trainable"])
        self.assertTrue(m["is_window_trainable"])
        self.assertEqual(report["stations"][0]["full_calendar_months_trainable"], 0)
        self.assertEqual(report["stations"][0]["partial_window_only_trainable_months"], 1)

    def test_paginated_raw_snapshot_save_and_offline_replay_reproducibility(self):
        rec_day1 = {
            "SiteId": "999", "SiteName": "合成站", "ItemEngName": "PM2.5",
            "ItemName": "細懸浮微粒", "ItemUnit": "μg/m3", "MonitorDate": "2026-11-23",
            **{f"MonitorValue{h:02d}": "15.0" for h in range(24)},
        }
        rec_day2 = {
            "SiteId": "999", "SiteName": "合成站", "ItemEngName": "PM2.5",
            "ItemName": "細懸浮微粒", "ItemUnit": "μg/m3", "MonitorDate": "2026-11-22",
            **{f"MonitorValue{h:02d}": "20.0" for h in range(24)},
        }
        client = MOENVClient("fake-secret-key-999", load_dotenv_file=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw_snapshot"
            with patch(
                "airguard.moenv.urlopen",
                side_effect=[_FakeHTTPResponse([rec_day1, rec_day2]), _FakeHTTPResponse([])],
            ):
                live_batch = client.fetch_pages(
                    "AQX_P_13",
                    limit=2,
                    start_offset=0,
                    max_pages=2,
                    station_id="999",
                    item_eng_name="PM2.5",
                    raw_dir=raw_dir,
                )

            # 確保任何快照檔案與 manifest 中均未寫入 API Key
            for file_path in raw_dir.iterdir():
                self.assertNotIn("fake-secret-key-999", file_path.read_text(encoding="utf-8"))

            # 離線從 raw_dir 重算，確認 SHA256、page_sha256s 與品質統計完全一致
            replayed = load_raw_snapshot(raw_dir)
            self.assertEqual(replayed["provenance"]["sha256"], live_batch["provenance"]["sha256"])
            self.assertEqual(replayed["provenance"]["page_sha256s"], live_batch["provenance"]["page_sha256s"])
            self.assertEqual(len(replayed["records"]), 2)

            out_buf = io.StringIO()
            with redirect_stdout(out_buf):
                rc = cli_main(["--dataset", "AQX_P_13", "--input", str(raw_dir), "--station-id", "999"])
            self.assertEqual(rc, 0)
            cli_report = json.loads(out_buf.getvalue())
            self.assertEqual(cli_report["provenance"]["sha256"], live_batch["provenance"]["sha256"])
            self.assertEqual(cli_report["quality"]["slots"], 48)
            self.assertEqual(cli_report["quality"]["ok"], 48)

            # 若原始分頁檔案被竄改，load_raw_snapshot 必須偵測 SHA256 不符並拋出 DataError
            page0_path = raw_dir / "page_0000_offset_0.json"
            page0_path.write_text("[]", encoding="utf-8")
            with self.assertRaises(DataError):
                load_raw_snapshot(raw_dir)


if __name__ == "__main__":
    unittest.main()

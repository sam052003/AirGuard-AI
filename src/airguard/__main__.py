"""CLI：離線資料／原始快照核對，或使用環境部 API Key 取得官方資料、保存原始快照與產出品質報告。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .moenv import (
    ALLOWED_DATASETS,
    ALLOWED_DUPLICATE_POLICIES,
    DATASET_DETAIL_URL,
    LICENSE_NOTES,
    MAX_VALID_PM25_UG_M3,
    SCHEMA_VERSION,
    DataError,
    FetchError,
    MOENVClient,
    load_raw_snapshot,
    parse_aqi,
    parse_historical_aqi,
    parse_hourly_pm25,
    parse_stations,
    quality_summary,
    station_month_quality_report,
    validate_station_id,
)


def _time_bounds(rows: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    timestamps: list[str] = []
    for row in rows:
        ts = row.get("observed_at_utc") or row.get("published_at_utc")
        if isinstance(ts, str) and ts:
            timestamps.append(ts)
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def _load_offline_input(input_path: Path, dataset: str, station_id: str | None) -> tuple[Any, dict[str, Any]]:
    """載入單一 JSON 檔案，或載入由 --raw-dir 保存的分頁原始快照目錄／manifest.json 並驗證 SHA256。"""
    if input_path.is_dir() or input_path.name == "manifest.json":
        snapshot = load_raw_snapshot(input_path)
        return snapshot["records"], snapshot["provenance"]

    raw_bytes = input_path.read_bytes()
    payload = json.loads(raw_bytes.decode("utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("pages"), list) and "records" not in payload:
        snapshot = load_raw_snapshot(input_path)
        return snapshot["records"], snapshot["provenance"]

    provenance = {
        "source_id": dataset,
        "source_url": f"{DATASET_DETAIL_URL}/{dataset}",
        "query_params_without_api_key": {"input": str(input_path)},
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "station_id": station_id,
        "license_notes": LICENSE_NOTES,
        "schema_version": SCHEMA_VERSION,
    }
    return payload, provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AirGuard W1 官方資料驗證與品質報告工具")
    parser.add_argument("--dataset", choices=sorted(ALLOWED_DATASETS), required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="讀取 JSON 檔或 --raw-dir 快照目錄／manifest.json；可離線重算驗證")
    source.add_argument("--live", action="store_true", help="使用環境部官方 API（需 MOENV_API_KEY 或 .env）")
    parser.add_argument("--raw-dir", type=Path, help="（--live 模式）保存各頁原始 API 回應 bytes 與 manifest.json 的本機目錄（建議位於 data/raw/）")
    parser.add_argument("--output", type=Path, help="輸出整理後的 JSONL（需審閱來源與授權）")
    parser.add_argument("--report-output", type=Path, help="輸出完整資料品質與來源追蹤 JSON 報告")
    parser.add_argument("--limit", type=int, default=1000, help="單頁筆數上限（1..1000）")
    parser.add_argument("--offset", type=int, default=0, help="起始分頁 offset")
    parser.add_argument("--max-pages", type=int, default=1, help="分頁擷取頁數（預設 1）")
    parser.add_argument("--station-id", type=str, help="篩選特定官方測站數字代碼（如臺中西屯 32）")
    parser.add_argument("--county", type=str, help="篩選縣市名稱（如 臺中市）")
    parser.add_argument(
        "--on-duplicate",
        choices=sorted(ALLOWED_DUPLICATE_POLICIES),
        default="error",
        help="AQX_P_13 同站同時刻重複紀錄處理策略（預設 error）",
    )
    parser.add_argument(
        "--max-pm25",
        type=float,
        default=MAX_VALID_PM25_UG_M3,
        help=f"PM2.5 合理物理上限門檻（μg/m³，預設 {MAX_VALID_PM25_UG_M3}；超過標記為 invalid）",
    )
    parser.add_argument("--env-file", type=Path, help="指定 .env 檔案路徑（預設為專案根目錄 .env）")
    args = parser.parse_args(argv)

    try:
        validated_station_id = validate_station_id(args.station_id) if args.station_id else None
        if args.input:
            payload, provenance = _load_offline_input(args.input, args.dataset, validated_station_id)
        else:
            client = MOENVClient(env_file=args.env_file)
            item_filter = "PM2.5" if args.dataset == "AQX_P_13" and validated_station_id else None
            fetched = client.fetch_pages(
                args.dataset,
                limit=args.limit,
                start_offset=args.offset,
                max_pages=args.max_pages,
                station_id=validated_station_id if args.dataset in {"AQX_P_13", "AQX_P_488"} else None,
                item_eng_name=item_filter,
                raw_dir=args.raw_dir,
            )
            payload = fetched["records"]
            provenance = fetched["provenance"]

        duplicate_log: list[dict[str, Any]] = []
        if args.dataset == "AQX_P_13":
            rows = parse_hourly_pm25(
                payload,
                on_duplicate=args.on_duplicate,
                duplicate_log=duplicate_log,
                station_id=validated_station_id,
                max_valid_pm25_ug_m3=args.max_pm25,
            )
        elif args.dataset == "AQX_P_432":
            rows = parse_aqi(
                payload,
                county=args.county,
                station_id=validated_station_id,
                max_valid_pm25_ug_m3=args.max_pm25,
            )
        elif args.dataset == "AQX_P_488":
            rows = parse_historical_aqi(
                payload,
                county=args.county,
                station_id=validated_station_id,
                max_valid_pm25_ug_m3=args.max_pm25,
            )
        else:
            rows = parse_stations(payload, county=args.county)

        min_time, max_time = _time_bounds(rows)
        provenance["record_count"] = len(rows)
        provenance["min_time"] = min_time
        provenance["max_time"] = max_time

        report: dict[str, Any] = {
            "dataset": args.dataset,
            "records": len(rows),
            "mode": "live" if args.live else "offline",
            "provenance": provenance,
        }
        if args.dataset == "AQX_P_13":
            report["quality"] = quality_summary(rows)
            report["station_month_quality"] = station_month_quality_report(
                rows,
                duplicate_log=duplicate_log,
                max_valid_pm25_ug_m3=args.max_pm25,
            )
        if args.raw_dir:
            report["raw_dir"] = str(args.raw_dir)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
                encoding="utf-8",
            )
            report["output"] = str(args.output)
        if args.report_output:
            args.report_output.parent.mkdir(parents=True, exist_ok=True)
            args.report_output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report["report_output"] = str(args.report_output)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, DataError, FetchError, json.JSONDecodeError) as exc:
        print(f"資料驗證失敗：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

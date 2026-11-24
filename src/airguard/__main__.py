"""CLI：離線資料核對或使用環境部 API Key 取得官方資料。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from .moenv import MOENVClient, DataError, FetchError, parse_aqi, parse_hourly_pm25, quality_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="AirGuard W1 官方資料驗證工具")
    parser.add_argument("--dataset", choices=["AQX_P_432", "AQX_P_13"], required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="讀取 JSON 檔；可以離線測試")
    source.add_argument("--live", action="store_true", help="使用環境部官方 API（需 MOENV_API_KEY）")
    parser.add_argument("--output", type=Path, help="輸出整理後的 JSONL（需審閱來源與授權）")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8-sig")) if args.input else MOENVClient().fetch(args.dataset, limit=args.limit)
        rows = parse_hourly_pm25(payload) if args.dataset == "AQX_P_13" else parse_aqi(payload)
        report = {"dataset": args.dataset, "records": len(rows), "mode": "live" if args.live else "offline"}
        if args.dataset == "AQX_P_13":
            report["quality"] = quality_summary(rows)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
            report["output"] = str(args.output)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, DataError, FetchError, json.JSONDecodeError) as exc:
        print(f"資料驗證失敗：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

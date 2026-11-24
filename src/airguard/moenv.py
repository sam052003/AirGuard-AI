"""環境部公開空品資料轉換器與唯讀 API 客戶端。

注意：AQI（官方多污染物指標）不等於 PM2.5（逐時質量濃度）。
所有時間使用時區資訊，不以取得時間冒充觀測／發布時間。
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TW = ZoneInfo("Asia/Taipei")
UTC = timezone.utc
BASE_URL = "https://data.moenv.gov.tw/api/v2"
ALLOWED_DATASETS = frozenset({"AQX_P_432", "AQX_P_488", "AQX_P_13", "AQX_P_07"})
MISSING_TOKENS = frozenset({"", "-", "--", "NA", "N/A", "NULL", "ND", "X", "*", "－"})


class DataError(ValueError):
    """來源內容不合資料契約；不可把缺值補成 0。"""


class FetchError(RuntimeError):
    """官方資料請求失敗；訊息不揭露 API Key。"""


def _fields(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def _number(raw: Any) -> tuple[float | None, str]:
    if raw is None or str(raw).strip().upper() in MISSING_TOKENS:
        return None, "missing"
    try:
        value = float(str(raw).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None, "invalid"
    if not math.isfinite(value) or value < 0:
        return None, "invalid"
    return value, "ok"


def _timestamp(raw: Any, *, allow_date: bool = False) -> datetime:
    if raw is None or not str(raw).strip():
        raise DataError("缺少觀測或發布時間")
    text = str(raw).strip()
    try:
        if text.endswith("Z"):
            result = datetime.fromisoformat(text[:-1] + "+00:00")
        else:
            result = datetime.fromisoformat(text)
    except ValueError:
        result = None
    if result is None:
        formats = ["%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]
        if allow_date:
            formats += ["%Y/%m/%d", "%Y-%m-%d"]
        for fmt in formats:
            try:
                result = datetime.strptime(text, fmt)
                break
            except ValueError:
                pass
    if result is None:
        raise DataError("無法解析日期或時間")
    if result.tzinfo is None:
        result = result.replace(tzinfo=TW)
    return result.astimezone(UTC)


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        source = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        source = payload["records"]
    else:
        raise DataError("JSON 缺少 records 陣列")
    if not all(isinstance(item, dict) for item in source):
        raise DataError("records 中出現非物件資料")
    return source


def parse_aqi(payload: Any, *, fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """讀取 AQX_P_432；發布時間缺失會明示 unknown，不捏造為即時。"""
    fetched_at = fetched_at or datetime.now(UTC)
    if fetched_at.tzinfo is None:
        raise DataError("fetched_at 必須含時區")
    output: list[dict[str, Any]] = []
    for item in _records(payload):
        row = _fields(item)
        station_id = str(row.get("siteid") or "").strip()
        if not station_id:
            raise DataError("AQI 紀錄缺少 SiteId")
        aqi, status = _number(row.get("aqi"))
        pm25, pm_status = _number(row.get("pm2.5"))
        timestamp = row.get("publishtime")
        published_at = None
        if timestamp is not None and str(timestamp).strip():
            published_at = _timestamp(timestamp).isoformat()
        output.append({
            "source_id": "AQX_P_432", "station_id": station_id,
            "station_name": row.get("sitename"), "county": row.get("county"),
            "official_aqi": int(aqi) if aqi is not None and aqi.is_integer() else aqi,
            "aqi_status": status,
            "observed_pm25_ug_m3": pm25, "pm25_status": pm_status,
            "published_at_utc": published_at,
            "retrieved_at_utc": fetched_at.astimezone(UTC).isoformat(),
        })
    return output


def parse_hourly_pm25(payload: Any) -> list[dict[str, Any]]:
    """將 AQX_P_13 的 MonitorValue00..23 寬表轉成逐時長表。

    每日 24 個觀測槽位都會保留；空值設為 null 和品質旗標。
    """
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in _records(payload):
        row = _fields(item)
        item_name = str(row.get("itemengname") or "").strip().upper().replace(" ", "")
        name_zh = str(row.get("itemname") or "").strip()
        if item_name not in {"PM2.5", "PM₂.₅"} and name_zh != "細懸浮微粒":
            continue
        station_id = str(row.get("siteid") or "").strip()
        if not station_id:
            raise DataError("逐時紀錄缺少 SiteId")
        unit = str(row.get("itemunit") or "").strip().replace(" ", "")
        if unit not in {"μg/m3", "μg/m³", "ug/m3", "ug/m³", "μg/m^3", "ug/m^3", "µg/m3", "µg/m³"}:
            raise DataError("PM2.5 單位不是可辨識的 μg/m³，拒絕自動換算")
        day = _timestamp(row.get("monitordate"), allow_date=True).astimezone(TW).date()
        for hour in range(24):
            raw = row.get(f"monitorvalue{hour:02d}")
            value, status = _number(raw)
            local_dt = datetime(day.year, day.month, day.day, hour, tzinfo=TW)
            obs_utc = local_dt.astimezone(UTC).isoformat()
            key = (station_id, obs_utc)
            if key in seen:
                raise DataError("重複的測站逐時 PM2.5 紀錄；需人工釐清資料版本")
            seen.add(key)
            result.append({
                "source_id": "AQX_P_13", "station_id": station_id,
                "station_name": row.get("sitename"),
                "pollutant": "PM2.5", "value_ug_m3": value,
                "quality_flag": status,
                "observed_at_utc": obs_utc,
                "published_at_utc": None,
                "averaging_window": "hourly",
            })
    return sorted(result, key=lambda r: (r["station_id"], r["observed_at_utc"]))


def quality_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    counts = {flag: sum(r.get("quality_flag") == flag for r in rows) for flag in ("ok", "missing", "invalid")}
    return {"slots": total, **counts, "valid_ratio": counts["ok"] / total if total else None}


class MOENVClient:
    """唯讀環境部 API 客戶端。只允許已審查的資料集代碼。"""

    def __init__(self, api_key: str | None = None, *, timeout: float = 15.0):
        self._key = api_key or os.environ.get("MOENV_API_KEY", "")
        if not self._key:
            raise ValueError("缺少 MOENV_API_KEY；請先至環境部申請會員 API Key")
        if timeout <= 0:
            raise ValueError("timeout 必須大於零")
        self.timeout = timeout

    def fetch(self, dataset: str, *, limit: int = 1000, offset: int = 0) -> dict[str, Any]:
        dataset = dataset.upper()
        if dataset not in ALLOWED_DATASETS:
            raise ValueError("不允許的資料集代碼")
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit 或 offset 超出允許範圍")
        query = urlencode({"api_key": self._key, "limit": limit, "offset": offset, "format": "JSON"})
        req = Request(f"{BASE_URL}/{dataset}?{query}", headers={"Accept": "application/json", "User-Agent": "AirGuard-AI/0.1"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise FetchError(f"環境部 API 擷取失敗（資料集 {dataset}；請檢查網路、授權與資料格式）") from None
        _records(data)
        return data

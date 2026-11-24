"""環境部公開空品資料轉換器、資料品質統計、原始快照重現與唯讀 API 客戶端。

注意：AQI（官方多污染物指標）不等於 PM2.5（逐時質量濃度）。
所有時間使用時區資訊，不以取得時間冒充觀測／發布時間。
"""
from __future__ import annotations

import calendar
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

try:
    from dotenv import dotenv_values as _dotenv_values
except ImportError:  # pragma: no cover - fallback when python-dotenv is not installed
    _dotenv_values = None

TW = ZoneInfo("Asia/Taipei")
UTC = timezone.utc
BASE_URL = "https://data.moenv.gov.tw/api/v2"
DATASET_DETAIL_URL = "https://data.moenv.gov.tw/dataset/detail"
ALLOWED_DATASETS = frozenset({"AQX_P_432", "AQX_P_488", "AQX_P_13", "AQX_P_07"})
MISSING_TOKENS = frozenset({"", "-", "--", "NA", "N/A", "NULL", "ND", "X", "*", "－"})
ALLOWED_DUPLICATE_POLICIES = frozenset({"error", "dedup_identical", "flag_conflict"})
VALID_PM25_UNITS = frozenset({"μg/m3", "μg/m³", "ug/m3", "ug/m³", "μg/m^3", "ug/m^3", "µg/m3", "µg/m³"})
# 依據環境部 AQI 計算濃度分段表，PM2.5 最高等級（AQI 500）上限為 500.4 μg/m³，
# 自動監測儀器量測物理上限通常為 1000 μg/m³；預設將 >1000 μg/m³ 視為儀器或傳輸異常（可透過參數調整或停用）。
MAX_VALID_PM25_UG_M3 = 1000.0
DEFAULT_DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"
STATION_ID_PATTERN = re.compile(r"^[0-9]{1,6}$")
ALLOWED_FILTER_ITEMS = frozenset({
    "PM2.5", "PM10", "O3", "SO2", "CO", "NO2", "NO", "NOx",
    "WIND_SPEED", "WIND_DIREC", "WS_HR", "WD_HR", "AMB_TEMP", "RH", "RAINFALL",
})
LICENSE_NOTES = "環境部資料開放平臺（政府資料開放授權條款-第1版）；僅供學術研究與系統驗證"
SCHEMA_VERSION = "w1.v1"


class DataError(ValueError):
    """來源內容不合資料契約；不可把缺值補成 0。"""


class FetchError(RuntimeError):
    """官方資料請求失敗；訊息不揭露 API Key。"""


def _parse_dotenv_fallback(path: Path) -> dict[str, str]:
    """當 python-dotenv 未安裝時的標準函式庫 .env 解析備援。"""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in {'"', "'"}:
            val = val[1:-1]
        elif " #" in val:
            val = val.split(" #", 1)[0].strip()
        if key:
            values[key] = val
    return values


def load_dotenv_dict(env_file: Path | str | None = None) -> dict[str, str]:
    """讀取 .env 檔案內容為字典，不直接覆寫全域 os.environ。"""
    path = Path(env_file) if env_file is not None else DEFAULT_DOTENV_PATH
    if not path.is_file():
        return {}
    if _dotenv_values is not None:
        raw = _dotenv_values(path, encoding="utf-8-sig")
        return {str(k): str(v).strip() for k, v in raw.items() if k and v is not None}
    return _parse_dotenv_fallback(path)


def resolve_api_key(
    api_key: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | str | None = None,
    load_dotenv_file: bool = True,
) -> str:
    """依優先序取得 MOENV_API_KEY：明確參數 > 非空系統環境變數 > .env 檔案。

    若系統環境變數 MOENV_API_KEY 未設定或為空字串，將自動回退讀取 .env（當 load_dotenv_file=True）。
    離線單元測試若需測試缺少金鑰，應傳入 load_dotenv_file=False 或指定測試用 env_file 以隔離本機真實 .env。
    """
    missing_msg = (
        "缺少 MOENV_API_KEY；請先至環境部資料開放平臺申請會員 API Key，"
        "於專案根目錄複製 .env.example 為 .env 並設定 MOENV_API_KEY，"
        "或在 PowerShell 設定 $env:MOENV_API_KEY"
    )
    if api_key is not None:
        cleaned = str(api_key).strip()
        if cleaned:
            return cleaned
        raise ValueError(missing_msg)

    env_map = os.environ if env is None else env
    sys_key = str(env_map.get("MOENV_API_KEY") or "").strip()
    if sys_key:
        return sys_key

    if load_dotenv_file:
        dotenv_map = load_dotenv_dict(env_file)
        file_key = str(dotenv_map.get("MOENV_API_KEY") or "").strip()
        if file_key:
            return file_key

    raise ValueError(missing_msg)


def validate_station_id(station_id: str) -> str:
    """驗證官方測站代碼（僅允許 1~6 位純數字 ID，阻擋 filter 語法注入）。"""
    sid = str(station_id or "").strip()
    if not STATION_ID_PATTERN.fullmatch(sid):
        raise ValueError("station_id 格式無效；僅允許 1 至 6 位數字測站代碼")
    return sid


def validate_item_eng_name(item_eng_name: str) -> str:
    """驗證官方測項英文代碼（僅允許已審查之白名單測項）。"""
    item = str(item_eng_name or "").strip()
    if item not in ALLOWED_FILTER_ITEMS:
        raise ValueError(f"item_eng_name 不在允許的測項白名單內：{item}")
    return item


def validate_moenv_filters(filters: str) -> str:
    """逐子句嚴格驗證環境部 API filters 語法，僅允許 siteid,EQ,<數字> 與 itemengname,EQ,<白名單測項>。"""
    cleaned = str(filters or "").strip()
    if not cleaned:
        raise ValueError("filters 不可為空字串")
    clauses = cleaned.split("|")
    normalized_clauses: list[str] = []
    for clause in clauses:
        parts = clause.split(",")
        if len(parts) != 3:
            raise ValueError("filters 子句格式無效；必須為 field,EQ,value")
        field, op, val = parts[0].strip().lower(), parts[1].strip().upper(), parts[2].strip()
        if op != "EQ":
            raise ValueError("filters 僅允許 EQ 相等比對運算子")
        if field == "siteid":
            normalized_clauses.append(f"siteid,EQ,{validate_station_id(val)}")
        elif field == "itemengname":
            normalized_clauses.append(f"itemengname,EQ,{validate_item_eng_name(val)}")
        else:
            raise ValueError(f"filters 不允許的查詢欄位：{field}")
    return "|".join(normalized_clauses)


def _fields(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def _normalize_county(text: Any) -> str:
    return str(text or "").strip().replace("台", "臺")


def _number(raw: Any, *, max_value: float | None = None) -> tuple[float | None, str]:
    if raw is None or str(raw).strip().upper() in MISSING_TOKENS:
        return None, "missing"
    try:
        value = float(str(raw).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None, "invalid"
    if not math.isfinite(value) or value < 0:
        return None, "invalid"
    if max_value is not None and value > max_value:
        return None, "invalid"
    return value, "ok"


def _coordinate(raw: Any, *, minimum: float, maximum: float, label: str) -> tuple[float | None, str]:
    if raw is None or str(raw).strip().upper() in MISSING_TOKENS:
        return None, "missing"
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise DataError(f"測站座標 {label} 格式無效") from exc
    if not math.isfinite(value) or not (minimum <= value <= maximum):
        raise DataError(f"測站座標 {label} 超出臺灣合理地理範圍")
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
        formats = ["%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]
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


def parse_stations(
    payload: Any,
    *,
    county: str | None = None,
    fetched_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """解析 AQX_P_07 官方測站基本資料，支援縣市過濾（自動正規化台／臺）。"""
    fetched_at = fetched_at or datetime.now(UTC)
    if fetched_at.tzinfo is None:
        raise DataError("fetched_at 必須含時區")
    target_county = _normalize_county(county) if county else None
    output: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in _records(payload):
        row = _fields(item)
        station_id = str(row.get("siteid") or "").strip()
        if not station_id:
            raise DataError("測站基本資料缺少 SiteId")
        station_name = str(row.get("sitename") or "").strip()
        if not station_name:
            raise DataError(f"測站 {station_id} 缺少 SiteName")
        raw_county = str(row.get("county") or "").strip() or None
        if target_county and _normalize_county(raw_county) != target_county:
            continue
        if station_id in seen_ids:
            raise DataError(f"重複的測站基本資料 SiteId：{station_id}")
        seen_ids.add(station_id)

        raw_lon = row.get("twd97lon") if row.get("twd97lon") is not None else row.get("longitude")
        raw_lat = row.get("twd97lat") if row.get("twd97lat") is not None else row.get("latitude")
        lon, lon_status = _coordinate(raw_lon, minimum=118.0, maximum=123.5, label="twd97lon")
        lat, lat_status = _coordinate(raw_lat, minimum=21.0, maximum=27.0, label="twd97lat")
        coord_ok = lon_status == "ok" and lat_status == "ok"

        output.append({
            "source_id": "AQX_P_07",
            "source_url": f"{DATASET_DETAIL_URL}/AQX_P_07",
            "station_id": station_id,
            "station_name": station_name,
            "station_eng_name": str(row.get("siteengname") or "").strip() or None,
            "area_name": str(row.get("areaname") or "").strip() or None,
            "county": raw_county,
            "township": str(row.get("township") or "").strip() or None,
            "site_address": str(row.get("siteaddress") or "").strip() or None,
            "site_type": str(row.get("sitetype") or "").strip() or None,
            "longitude_twd97": lon if coord_ok else None,
            "latitude_twd97": lat if coord_ok else None,
            "coordinate_system": "TWD97" if coord_ok else None,
            "coordinate_status": "ok" if coord_ok else "missing",
            "retrieved_at_utc": fetched_at.astimezone(UTC).isoformat(),
        })

    return sorted(
        output,
        key=lambda r: (0, int(r["station_id"])) if str(r["station_id"]).isdigit() else (1, str(r["station_id"])),
    )


def parse_aqi(
    payload: Any,
    *,
    fetched_at: datetime | None = None,
    county: str | None = None,
    station_id: str | None = None,
    max_valid_pm25_ug_m3: float | None = MAX_VALID_PM25_UG_M3,
) -> list[dict[str, Any]]:
    """讀取 AQX_P_432；發布時間缺失會明示 unknown，不捏造為即時。"""
    fetched_at = fetched_at or datetime.now(UTC)
    if fetched_at.tzinfo is None:
        raise DataError("fetched_at 必須含時區")
    target_county = _normalize_county(county) if county else None
    target_station = validate_station_id(station_id) if station_id else None
    output: list[dict[str, Any]] = []
    for item in _records(payload):
        row = _fields(item)
        sid = str(row.get("siteid") or "").strip()
        if not sid:
            raise DataError("AQI 紀錄缺少 SiteId")
        if target_station and sid != target_station:
            continue
        if target_county and _normalize_county(row.get("county")) != target_county:
            continue
        aqi, status = _number(row.get("aqi"))
        pm25, pm_status = _number(row.get("pm2.5"), max_value=max_valid_pm25_ug_m3)
        timestamp = row.get("publishtime")
        published_at = None
        if timestamp is not None and str(timestamp).strip():
            published_at = _timestamp(timestamp).isoformat()
        output.append({
            "source_id": "AQX_P_432", "station_id": sid,
            "station_name": row.get("sitename"), "county": row.get("county"),
            "official_aqi": int(aqi) if aqi is not None and aqi.is_integer() else aqi,
            "aqi_status": status,
            "observed_pm25_ug_m3": pm25, "pm25_status": pm_status,
            "published_at_utc": published_at,
            "retrieved_at_utc": fetched_at.astimezone(UTC).isoformat(),
        })
    return output


def parse_historical_aqi(
    payload: Any,
    *,
    fetched_at: datetime | None = None,
    county: str | None = None,
    station_id: str | None = None,
    max_valid_pm25_ug_m3: float | None = MAX_VALID_PM25_UG_M3,
) -> list[dict[str, Any]]:
    """解析 AQX_P_488 歷史 AQI；嚴格區分官方 AQI、當小時 PM2.5 與移動平均 PM2.5_AVG。"""
    fetched_at = fetched_at or datetime.now(UTC)
    if fetched_at.tzinfo is None:
        raise DataError("fetched_at 必須含時區")
    target_county = _normalize_county(county) if county else None
    target_station = validate_station_id(station_id) if station_id else None
    output: list[dict[str, Any]] = []

    for item in _records(payload):
        row = _fields(item)
        sid = str(row.get("siteid") or "").strip()
        if not sid:
            raise DataError("歷史 AQI 紀錄缺少 SiteId")
        if target_station and sid != target_station:
            continue
        if target_county and _normalize_county(row.get("county")) != target_county:
            continue
        raw_time = row.get("datacreationdate") or row.get("publishtime")
        observed_at = _timestamp(raw_time).isoformat()
        aqi, aqi_status = _number(row.get("aqi"))
        pm25, pm25_status = _number(row.get("pm2.5"), max_value=max_valid_pm25_ug_m3)
        pm25_avg, pm25_avg_status = _number(row.get("pm2.5_avg"), max_value=max_valid_pm25_ug_m3)
        wind_speed, _ = _number(row.get("windspeed") if row.get("windspeed") is not None else row.get("wind_speed"))
        wind_direc, _ = _number(row.get("winddirec") if row.get("winddirec") is not None else row.get("wind_direc"))

        output.append({
            "source_id": "AQX_P_488",
            "station_id": sid,
            "station_name": row.get("sitename"),
            "county": row.get("county"),
            "official_aqi": int(aqi) if aqi is not None and aqi.is_integer() else aqi,
            "aqi_status": aqi_status,
            "aqi_category": str(row.get("status") or "").strip() or None,
            "main_pollutant": str(row.get("pollutant") or "").strip() or None,
            "observed_pm25_ug_m3": pm25,
            "pm25_status": pm25_status,
            "pm25_moving_avg_ug_m3": pm25_avg,
            "pm25_moving_avg_status": pm25_avg_status,
            "wind_speed_m_s": wind_speed,
            "wind_direction_deg": wind_direc,
            "observed_at_utc": observed_at,
            "published_at_utc": None,
            "retrieved_at_utc": fetched_at.astimezone(UTC).isoformat(),
        })
    return sorted(output, key=lambda r: (r["station_id"], r["observed_at_utc"]))


def parse_hourly_pm25(
    payload: Any,
    *,
    on_duplicate: str = "error",
    duplicate_log: list[dict[str, Any]] | None = None,
    station_id: str | None = None,
    max_valid_pm25_ug_m3: float | None = MAX_VALID_PM25_UG_M3,
) -> list[dict[str, Any]]:
    """將 AQX_P_13 的 MonitorValue00..23 寬表轉成逐時長表。

    每日 24 個觀測槽位都會保留；空值設為 null 和品質旗標。
    同站同時刻重複紀錄依 on_duplicate 處理（預設 'error' 拒絕；'dedup_identical' 僅合併完全相同紀錄並留存稽核；
    'flag_conflict' 先保存既有值與旗標至 duplicate_log，再將衝突時槽標示為 invalid 且設為 null，絕不靜默覆蓋）。
    """
    if on_duplicate not in ALLOWED_DUPLICATE_POLICIES:
        raise ValueError(f"不支援的重複資料處理策略：{on_duplicate}")
    if max_valid_pm25_ug_m3 is not None and max_valid_pm25_ug_m3 <= 0:
        raise ValueError("max_valid_pm25_ug_m3 必須大於零或為 None")
    target_station = validate_station_id(station_id) if station_id else None
    slots_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for item in _records(payload):
        row = _fields(item)
        item_name = str(row.get("itemengname") or "").strip().upper().replace(" ", "")
        name_zh = str(row.get("itemname") or "").strip()
        if item_name not in {"PM2.5", "PM₂.₅"} and name_zh != "細懸浮微粒":
            continue
        sid = str(row.get("siteid") or "").strip()
        if not sid:
            raise DataError("逐時紀錄缺少 SiteId")
        if target_station and sid != target_station:
            continue
        unit = str(row.get("itemunit") or "").strip().replace(" ", "")
        if unit not in VALID_PM25_UNITS:
            raise DataError("PM2.5 單位不是可辨識的 μg/m³，拒絕自動換算")
        day = _timestamp(row.get("monitordate"), allow_date=True).astimezone(TW).date()
        for hour in range(24):
            raw = row.get(f"monitorvalue{hour:02d}")
            value, status = _number(raw, max_value=max_valid_pm25_ug_m3)
            local_dt = datetime(day.year, day.month, day.day, hour, tzinfo=TW)
            obs_utc = local_dt.astimezone(UTC).isoformat()
            key = (sid, obs_utc)
            candidate = {
                "source_id": "AQX_P_13", "station_id": sid,
                "station_name": row.get("sitename"),
                "pollutant": "PM2.5", "value_ug_m3": value,
                "quality_flag": status,
                "observed_at_utc": obs_utc,
                "published_at_utc": None,
                "averaging_window": "hourly",
            }
            if key in slots_by_key:
                if on_duplicate == "error":
                    raise DataError("重複的測站逐時 PM2.5 紀錄；需人工釐清資料版本")
                existing = slots_by_key[key]
                is_identical = (
                    existing["value_ug_m3"] == candidate["value_ug_m3"]
                    and existing["quality_flag"] == candidate["quality_flag"]
                )
                if is_identical:
                    if duplicate_log is not None:
                        duplicate_log.append({
                            "station_id": sid,
                            "observed_at_utc": obs_utc,
                            "strategy": on_duplicate,
                            "resolution": "identical_kept",
                            "value_ug_m3": value,
                            "quality_flag": status,
                        })
                    continue
                if on_duplicate == "dedup_identical":
                    raise DataError(
                        f"同站同時刻出現數值衝突的重複 PM2.5 紀錄（station_id={sid}, observed_at_utc={obs_utc}）"
                    )
                # on_duplicate == "flag_conflict": 先保存衝突前原始數值與旗標，再將該時槽設為 None / invalid
                previous_value = existing["value_ug_m3"]
                previous_flag = existing["quality_flag"]
                existing["value_ug_m3"] = None
                existing["quality_flag"] = "invalid"
                if duplicate_log is not None:
                    duplicate_log.append({
                        "station_id": sid,
                        "observed_at_utc": obs_utc,
                        "strategy": on_duplicate,
                        "resolution": "conflict_flagged_invalid",
                        "previous_value_ug_m3": previous_value,
                        "previous_quality_flag": previous_flag,
                        "conflicting_value_ug_m3": value,
                        "conflicting_quality_flag": status,
                    })
                continue
            slots_by_key[key] = candidate
    return sorted(slots_by_key.values(), key=lambda r: (r["station_id"], r["observed_at_utc"]))


def quality_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    counts = {flag: sum(r.get("quality_flag") == flag for r in rows) for flag in ("ok", "missing", "invalid")}
    return {"slots": total, **counts, "valid_ratio": counts["ok"] / total if total else None}


def _max_consecutive_non_valid(
    slot_map: Mapping[datetime, dict[str, Any]],
    first_dt: datetime,
    last_dt: datetime,
) -> int:
    max_streak = 0
    current_streak = 0
    cursor = first_dt
    step = timedelta(hours=1)
    while cursor <= last_dt:
        rec = slot_map.get(cursor)
        if rec is not None and rec.get("quality_flag") == "ok" and rec.get("value_ug_m3") is not None:
            current_streak = 0
        else:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        cursor += step
    return max_streak


def station_month_quality_report(
    rows: list[dict[str, Any]],
    *,
    duplicate_log: list[dict[str, Any]] | None = None,
    min_trainable_coverage: float = 0.8,
    min_trainable_hours: int = 336,
    max_valid_pm25_ug_m3: float | None = MAX_VALID_PM25_UG_M3,
) -> dict[str, Any]:
    """計算每站 × 每月（以 Asia/Taipei 日曆月對齊）的資料完整率、最大連續缺失與 1/3/6h 有效預測樣本對數。

    明確區分：
    - is_calendar_month_trainable：整月日曆完整率（valid_hours / expected_hours）>= min_trainable_coverage 且有效時數達標。
    - is_window_trainable（同 is_trainable）：已觀測片段視窗內完整率（valid_hours / window_expected_hours）>= min_trainable_coverage 且有效時數達標。
    """
    by_station: dict[str, dict[datetime, dict[str, Any]]] = defaultdict(dict)
    by_station_month: dict[tuple[str, str], list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    station_names: dict[str, str | None] = {}

    for row in rows:
        sid = str(row["station_id"])
        station_names.setdefault(sid, row.get("station_name"))
        dt_utc = _timestamp(row["observed_at_utc"])
        dt_local = dt_utc.astimezone(TW)
        ym = f"{dt_local.year:04d}-{dt_local.month:02d}"
        by_station[sid][dt_utc] = row
        by_station_month[(sid, ym)].append((dt_utc, row))

    monthly_reports: list[dict[str, Any]] = []
    for (sid, ym) in sorted(by_station_month.keys()):
        items = sorted(by_station_month[(sid, ym)], key=lambda x: x[0])
        year_int, month_int = (int(part) for part in ym.split("-", 1))
        calendar_expected = calendar.monthrange(year_int, month_int)[1] * 24
        first_dt = items[0][0]
        last_dt = items[-1][0]
        window_expected = int((last_dt - first_dt).total_seconds() // 3600) + 1
        slot_map = {dt: rec for dt, rec in items}
        actual_slots = len(items)
        ok_count = sum(1 for _, r in items if r.get("quality_flag") == "ok" and r.get("value_ug_m3") is not None)
        recorded_missing = sum(1 for _, r in items if r.get("quality_flag") == "missing")
        invalid_count = sum(1 for _, r in items if r.get("quality_flag") == "invalid")
        unobserved_calendar = max(0, calendar_expected - actual_slots)
        unobserved_window = max(0, window_expected - actual_slots)
        max_consecutive_missing = _max_consecutive_non_valid(slot_map, first_dt, last_dt)

        station_all_slots = by_station[sid]
        horizon_pairs: dict[str, int] = {}
        for h in (1, 3, 6):
            delta = timedelta(hours=h)
            valid_pairs = 0
            for dt_utc, rec in items:
                if rec.get("quality_flag") != "ok" or rec.get("value_ug_m3") is None:
                    continue
                target_rec = station_all_slots.get(dt_utc + delta)
                if target_rec is not None and target_rec.get("quality_flag") == "ok" and target_rec.get("value_ug_m3") is not None:
                    valid_pairs += 1
            horizon_pairs[f"{h}h"] = valid_pairs

        calendar_cov = ok_count / calendar_expected if calendar_expected else None
        window_cov = ok_count / window_expected if window_expected else None
        slot_cov = ok_count / actual_slots if actual_slots else None
        is_window_trainable = bool(
            ok_count >= min_trainable_hours
            and window_cov is not None
            and window_cov >= min_trainable_coverage
        )
        is_calendar_month_trainable = bool(
            ok_count >= min_trainable_hours
            and calendar_cov is not None
            and calendar_cov >= min_trainable_coverage
        )
        is_full_calendar_span = bool(window_expected == calendar_expected)

        monthly_reports.append({
            "station_id": sid,
            "station_name": station_names.get(sid),
            "year_month_local": ym,
            "timezone_grouping": "Asia/Taipei",
            "expected_hours": calendar_expected,
            "window_expected_hours": window_expected,
            "actual_slots": actual_slots,
            "valid_hours": ok_count,
            "missing_hours": recorded_missing,
            "unobserved_hours": unobserved_calendar,
            "window_unobserved_hours": unobserved_window,
            "invalid_hours": invalid_count,
            "coverage": round(calendar_cov, 6) if calendar_cov is not None else None,
            "calendar_coverage": round(calendar_cov, 6) if calendar_cov is not None else None,
            "window_coverage": round(window_cov, 6) if window_cov is not None else None,
            "slot_coverage": round(slot_cov, 6) if slot_cov is not None else None,
            "first_observed_at_utc": first_dt.isoformat(),
            "last_observed_at_utc": last_dt.isoformat(),
            "first_observed_at_local": first_dt.astimezone(TW).isoformat(),
            "last_observed_at_local": last_dt.astimezone(TW).isoformat(),
            "max_consecutive_missing_hours": max_consecutive_missing,
            "horizon_valid_pairs": horizon_pairs,
            "is_full_calendar_span": is_full_calendar_span,
            "is_calendar_month_trainable": is_calendar_month_trainable,
            "is_window_trainable": is_window_trainable,
            "is_trainable": is_window_trainable,
            "backtest_availability_note": "reconstructed_from_observed_at",
        })

    station_summaries: list[dict[str, Any]] = []
    for sid in sorted(by_station.keys()):
        slot_map = by_station[sid]
        dts = sorted(slot_map.keys())
        first_dt, last_dt = dts[0], dts[-1]
        window_expected = int((last_dt - first_dt).total_seconds() // 3600) + 1
        actual_slots = len(dts)
        ok_count = sum(1 for r in slot_map.values() if r.get("quality_flag") == "ok" and r.get("value_ug_m3") is not None)
        missing_count = sum(1 for r in slot_map.values() if r.get("quality_flag") == "missing")
        invalid_count = sum(1 for r in slot_map.values() if r.get("quality_flag") == "invalid")
        horizon_pairs = {}
        for h in (1, 3, 6):
            delta = timedelta(hours=h)
            horizon_pairs[f"{h}h"] = sum(
                1
                for dt_utc, rec in slot_map.items()
                if rec.get("quality_flag") == "ok"
                and rec.get("value_ug_m3") is not None
                and (dt_utc + delta) in slot_map
                and slot_map[dt_utc + delta].get("quality_flag") == "ok"
                and slot_map[dt_utc + delta].get("value_ug_m3") is not None
            )
        station_months_for_sid = [m for m in monthly_reports if m["station_id"] == sid]
        full_cal_trainable = sum(1 for m in station_months_for_sid if m["is_calendar_month_trainable"])
        window_trainable = sum(1 for m in station_months_for_sid if m["is_window_trainable"])
        station_summaries.append({
            "station_id": sid,
            "station_name": station_names.get(sid),
            "months_covered": len(station_months_for_sid),
            "full_calendar_months_trainable": full_cal_trainable,
            "partial_window_only_trainable_months": window_trainable - full_cal_trainable,
            "trainable_months": window_trainable,
            "window_expected_hours": window_expected,
            "actual_slots": actual_slots,
            "valid_hours": ok_count,
            "missing_hours": missing_count,
            "unobserved_window_hours": max(0, window_expected - actual_slots),
            "invalid_hours": invalid_count,
            "window_coverage": round(ok_count / window_expected, 6) if window_expected else None,
            "slot_coverage": round(ok_count / actual_slots, 6) if actual_slots else None,
            "first_observed_at_utc": first_dt.isoformat(),
            "last_observed_at_utc": last_dt.isoformat(),
            "first_observed_at_local": first_dt.astimezone(TW).isoformat(),
            "last_observed_at_local": last_dt.astimezone(TW).isoformat(),
            "max_consecutive_missing_hours": _max_consecutive_non_valid(slot_map, first_dt, last_dt),
            "horizon_valid_pairs": horizon_pairs,
            "backtest_availability_note": "reconstructed_from_observed_at",
        })

    dup_entries = duplicate_log or []
    return {
        "schema_version": SCHEMA_VERSION,
        "backtest_mode": "reconstructed_from_observed_at",
        "qc_thresholds": {
            "min_valid_pm25_ug_m3": 0.0,
            "max_valid_pm25_ug_m3": max_valid_pm25_ug_m3,
            "max_pm25_reference": (
                "MOENV AQI PM2.5 breakpoint table upper bound is 500.4 ug/m3 (AQI 500); "
                "1000.0 ug/m3 is the default hourly instrument anomaly threshold (configurable via --max-pm25)."
            ),
        },
        "trainable_criteria": {
            "min_trainable_coverage": min_trainable_coverage,
            "min_trainable_hours": min_trainable_hours,
            "window_trainable_definition": "valid_hours >= min_trainable_hours and (valid_hours / window_expected_hours) >= min_trainable_coverage",
            "calendar_month_trainable_definition": "valid_hours >= min_trainable_hours and (valid_hours / expected_hours) >= min_trainable_coverage",
        },
        "duplicate_summary": {
            "duplicate_slots_detected": len(dup_entries),
            "identical_kept": sum(1 for d in dup_entries if d.get("resolution") == "identical_kept"),
            "conflict_flagged_invalid": sum(1 for d in dup_entries if d.get("resolution") == "conflict_flagged_invalid"),
        },
        "stations": station_summaries,
        "station_months": monthly_reports,
    }


def build_moenv_filters(*, station_id: str | None = None, item_eng_name: str | None = None) -> str | None:
    """組合環境部 API v2 支援的 filters 查詢參數（依欄位型別嚴格驗證，不含任何憑證）。"""
    clauses: list[str] = []
    if station_id is not None and str(station_id).strip():
        clauses.append(f"siteid,EQ,{validate_station_id(station_id)}")
    if item_eng_name is not None and str(item_eng_name).strip():
        clauses.append(f"itemengname,EQ,{validate_item_eng_name(item_eng_name)}")
    return "|".join(clauses) if clauses else None


def load_raw_snapshot(snapshot_path: Path) -> dict[str, Any]:
    """從 --raw-dir 儲存的本機快照目錄（或 manifest.json）載入各頁原始 bytes 並驗證 SHA256。"""
    manifest_file = snapshot_path / "manifest.json" if snapshot_path.is_dir() else snapshot_path
    if not manifest_file.is_file():
        raise DataError(f"找不到原始快照 manifest：{manifest_file}")
    base_dir = manifest_file.parent
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise DataError("原始快照 manifest 缺少有效的 pages 清單")

    combined_records: list[dict[str, Any]] = []
    page_sha256s: list[str] = []
    batch_hasher = hashlib.sha256()

    for page_meta in pages:
        rel_name = page_meta.get("file")
        expected_sha = page_meta.get("sha256")
        if not rel_name or not expected_sha:
            raise DataError("原始快照 manifest 的 page 項目缺少 file 或 sha256")
        page_file = (base_dir / rel_name).resolve()
        if page_file.parent != base_dir.resolve() or not page_file.is_file():
            raise DataError(f"原始快照分頁檔案不存在或路徑不合法：{rel_name}")
        raw_bytes = page_file.read_bytes()
        actual_sha = hashlib.sha256(raw_bytes).hexdigest()
        if actual_sha != expected_sha:
            raise DataError(
                f"原始快照分頁 {rel_name} 的 SHA256 不符（預期 {expected_sha}，實得 {actual_sha}）"
            )
        page_sha256s.append(actual_sha)
        batch_hasher.update(actual_sha.encode("ascii"))
        page_data = json.loads(raw_bytes.decode("utf-8-sig"))
        combined_records.extend(_records(page_data))

    computed_batch_sha = page_sha256s[0] if len(page_sha256s) == 1 else batch_hasher.hexdigest()
    expected_batch_sha = manifest.get("sha256")
    if expected_batch_sha and computed_batch_sha != expected_batch_sha:
        raise DataError(
            f"原始快照批次 SHA256 不符（預期 {expected_batch_sha}，實得 {computed_batch_sha}）"
        )

    provenance = {
        "source_id": manifest.get("source_id"),
        "source_url": manifest.get("source_url"),
        "query_params_without_api_key": manifest.get("query_params_without_api_key"),
        "retrieved_at_utc": manifest.get("retrieved_at_utc"),
        "sha256": computed_batch_sha,
        "page_sha256s": page_sha256s,
        "record_count": len(combined_records),
        "station_id": manifest.get("station_id"),
        "license_notes": manifest.get("license_notes", LICENSE_NOTES),
        "schema_version": manifest.get("schema_version", SCHEMA_VERSION),
        "replayed_from_snapshot": str(manifest_file),
    }
    return {"records": combined_records, "provenance": provenance}


class MOENVClient:
    """唯讀環境部 API 客戶端。只允許已審查的資料集代碼。"""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 20.0,
        env_file: Path | str | None = None,
        load_dotenv_file: bool = True,
    ):
        self._key = resolve_api_key(
            api_key,
            env_file=env_file,
            load_dotenv_file=load_dotenv_file,
        )
        if timeout <= 0:
            raise ValueError("timeout 必須大於零")
        self.timeout = timeout

    def _validate_request_args(
        self,
        dataset: str,
        *,
        limit: int,
        offset: int,
        filters: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        dataset = dataset.upper()
        if dataset not in ALLOWED_DATASETS:
            raise ValueError("不允許的資料集代碼")
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit 或 offset 超出允許範圍")
        public_params: dict[str, Any] = {"limit": limit, "offset": offset, "format": "JSON"}
        if filters is not None and str(filters).strip():
            public_params["filters"] = validate_moenv_filters(filters)
        return dataset, public_params

    def fetch_page_with_metadata(
        self,
        dataset: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        filters: str | None = None,
    ) -> dict[str, Any]:
        """擷取單頁官方資料並回傳 records、原始 payload、raw_bytes 與不含金鑰的可重現來源雜湊（SHA256）。"""
        dataset, public_params = self._validate_request_args(
            dataset, limit=limit, offset=offset, filters=filters
        )
        query = urlencode({"api_key": self._key, **public_params})
        req = Request(
            f"{BASE_URL}/{dataset}?{query}",
            headers={"Accept": "application/json", "User-Agent": "AirGuard-AI/0.1"},
        )
        retrieved_at = datetime.now(UTC)
        try:
            with urlopen(req, timeout=self.timeout) as response:
                if hasattr(response, "read"):
                    raw_bytes = response.read()
                    if isinstance(raw_bytes, str):
                        raw_bytes = raw_bytes.encode("utf-8")
                    data = json.loads(raw_bytes.decode("utf-8-sig"))
                else:  # pragma: no cover
                    data = json.load(response)
                    raw_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise FetchError(
                f"環境部 API 擷取失敗（資料集 {dataset}；請檢查網路、授權與資料格式）"
            ) from None
        records = _records(data)
        sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
        return {
            "payload": data,
            "records": records,
            "raw_bytes": raw_bytes,
            "provenance": {
                "source_id": dataset,
                "source_url": f"{DATASET_DETAIL_URL}/{dataset}",
                "query_params_without_api_key": public_params,
                "retrieved_at_utc": retrieved_at.isoformat(),
                "sha256": sha256_hex,
                "record_count": len(records),
                "license_notes": LICENSE_NOTES,
                "schema_version": SCHEMA_VERSION,
            },
        }

    def fetch(
        self,
        dataset: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        filters: str | None = None,
    ) -> Any:
        """擷取單頁官方資料（相容既有介面）。"""
        return self.fetch_page_with_metadata(
            dataset, limit=limit, offset=offset, filters=filters
        )["payload"]

    def fetch_pages(
        self,
        dataset: str,
        *,
        limit: int = 500,
        start_offset: int = 0,
        max_pages: int = 2,
        filters: str | None = None,
        station_id: str | None = None,
        item_eng_name: str | None = None,
        raw_dir: Path | str | None = None,
    ) -> dict[str, Any]:
        """分頁擷取多頁官方資料，保存每頁與整體的 SHA256、查詢參數與擷取時間；若指定 raw_dir 則保存原始各頁 bytes 與 manifest.json。"""
        if max_pages < 1 or max_pages > 50:
            raise ValueError("max_pages 必須介於 1 與 50 之間")
        effective_filters = (
            validate_moenv_filters(filters)
            if filters is not None and str(filters).strip()
            else build_moenv_filters(station_id=station_id, item_eng_name=item_eng_name)
        )
        combined_records: list[dict[str, Any]] = []
        page_provenances: list[dict[str, Any]] = []
        manifest_pages: list[dict[str, Any]] = []
        batch_hasher = hashlib.sha256()

        target_raw_dir = Path(raw_dir) if raw_dir is not None else None
        if target_raw_dir is not None:
            target_raw_dir.mkdir(parents=True, exist_ok=True)

        for page_index in range(max_pages):
            current_offset = start_offset + page_index * limit
            page = self.fetch_page_with_metadata(
                dataset,
                limit=limit,
                offset=current_offset,
                filters=effective_filters,
            )
            recs = page["records"]
            prov = page["provenance"]
            raw_bytes = page["raw_bytes"]
            page_provenances.append(prov)
            batch_hasher.update(prov["sha256"].encode("ascii"))
            combined_records.extend(recs)

            page_filename = f"page_{page_index:04d}_offset_{current_offset}.json"
            if target_raw_dir is not None:
                (target_raw_dir / page_filename).write_bytes(raw_bytes)
            manifest_pages.append({
                "page_index": page_index,
                "offset": current_offset,
                "limit": limit,
                "file": page_filename,
                "sha256": prov["sha256"],
                "record_count": len(recs),
                "retrieved_at_utc": prov["retrieved_at_utc"],
                "query_params_without_api_key": prov["query_params_without_api_key"],
            })
            if len(recs) < limit:
                break

        retrieved_at_utc = (
            page_provenances[-1]["retrieved_at_utc"]
            if page_provenances
            else datetime.now(UTC).isoformat()
        )
        batch_sha256 = (
            page_provenances[0]["sha256"]
            if len(page_provenances) == 1
            else batch_hasher.hexdigest()
        )
        provenance: dict[str, Any] = {
            "source_id": dataset.upper(),
            "source_url": f"{DATASET_DETAIL_URL}/{dataset.upper()}",
            "query_params_without_api_key": {
                "limit": limit,
                "start_offset": start_offset,
                "max_pages_requested": max_pages,
                "pages_fetched": len(page_provenances),
                "filters": effective_filters,
                "format": "JSON",
            },
            "retrieved_at_utc": retrieved_at_utc,
            "sha256": batch_sha256,
            "page_sha256s": [p["sha256"] for p in page_provenances],
            "record_count": len(combined_records),
            "station_id": validate_station_id(station_id) if station_id else None,
            "license_notes": LICENSE_NOTES,
            "schema_version": SCHEMA_VERSION,
        }
        if target_raw_dir is not None:
            manifest_path = target_raw_dir / "manifest.json"
            manifest_payload = {
                **provenance,
                "pages": manifest_pages,
            }
            manifest_path.write_text(
                json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            provenance["raw_snapshot_manifest"] = str(manifest_path)

        return {
            "records": combined_records,
            "provenance": provenance,
        }

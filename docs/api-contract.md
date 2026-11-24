# AirGuard AI｜API Contract v0.1（設計契約，尚未部署）

**重要**：此處是前後端、Agent 與測試共用的**待實作契約**；目前僅 W1 資料解析 CLI 可運作，以下 Web API **不是已上線端點**。若變更需提交 PR，先改契約與測試再改程式。JSON Schema 參考 [query](schemas/query.schema.json)、[response](schemas/report.schema.json)。

## 基本規則
- Base URL：本機規劃 `/api/v1`（不宣稱存在）；採 JSON UTF-8，時間一律含時區的 RFC 3339／ISO 8601，顯示預設 `Asia/Taipei`，儲存 UTC。
- `source_id`、`station_id`、`observed_at`／`published_at`／`retrieved_at`、`unit`、`averaging_window`、`quality_flag` 必須有明確語意；未知的發佈時間是 `null`，不能以擷取時間偽裝。
- 官方 `aqi` 數值與模型 `pm25_ug_m3` 分開；預測距離僅 `[1,3,6]` 小時（並不代表其他時距允許模型外插）。
- 無資料回 `null` 加上明確狀態；不得以 0、空來源、無版本資訊假裝可靠觀測。
- API Key 僅在後端讀取系統環境變數 `MOENV_API_KEY` 或本機 `.env`（系統環境變數優先）；不放 query logs、response、前端或 GitHub。
- W1 CLI 與資料層已實作 `AQX_P_07`（含 `longitude_twd97`、`latitude_twd97`、`coordinate_system="TWD97"`、`coordinate_status`）、`AQX_P_432`、`AQX_P_488`（區分 `official_aqi`、`observed_pm25_ug_m3` 與 `pm25_moving_avg_ug_m3`）及 `AQX_P_13`（含 `station_month_quality_report`、`horizon_valid_pairs` 與 `provenance.sha256`）。
- 預估暴露 `exposure_index_ug_h_m3 = Σ(C_ug_m3 × duration_h)` 為**測站尺度濃度–時間估算**，不等於個人吸入劑量或健康安全閾值。

## 規劃的端點

| Endpoint | Request | Response／限制 |
|---|---|---|
| `GET /api/v1/stations` | optional `county`, `limit` | `stations[]`：site ID、name、官方座標、來源與取得時間；若來源沒有可驗證座標，標 null |
| `GET /api/v1/aqi?station_id=...` | 必填 `station_id` | `official_aqi`：官方發布值、PM2.5 觀測值（不同欄位）、發布／取得時間、freshness |
| `GET /api/v1/history?station_id=...&start_at=...&end_at=...` | 測站＋時間範圍 | `observations[]`，缺失與品質報告、來源版本；限制分頁，禁止不受控全表 |
| `POST /api/v1/forecast` | `station_id`, `as_of`, `horizon_hours`∈{1,3,6} | `forecast`：模型版本、測站尺度、預測時間、值、誤差／不確定性、資料版次；尚未訓練時 `unavailable` |
| `POST /api/v1/activity/estimate` | `station_id`, segments，每段有 `concentration_ug_m3`／`duration_h`／source | `exposure_index_ug_h_m3`, `coverage_ratio`；若缺段需 partial/unknown，不當零 |
| `POST /api/v1/agent/query` | 參照 `query.schema.json`；自然語言與可選站點、時段、活動、族群 | `report.schema.json`：來源、限制、官方 AQI、1/3/6h PM2.5、時段決策及 trace |

## HTTP 與應用程式狀態
- `200` + `status=ok|partial`：成功或可理解的部分資訊（partial 需說明缺少哪些）。
- `400`／`422` + `status=needs_input`：缺參數、時間／位置歧義；提供欄位提示。
- `422` + `status=out_of_horizon`：超出目前支援模型時距，絕不外插精確值。
- `503` + `status=unavailable`：來源、模型、金鑰或依賴服務失效；若有合法舊快取，僅列為歷史快照。
- `500`：未預期錯誤需追蹤 trace_id，但**不得洩露金鑰或詳細內部憑證**。未定義完整的 FastAPI exception handler 前不宣稱已實作。

## Agent 查詢／回覆示例（**合成示例**）
請參考 [request](examples/agent-query-request.json)、[response](examples/agent-query-response.json)。示例內 999 號站點與 AQI 為**合成測試值**，不能顯示為臺灣目前即時 AQI；`status=unavailable` 說明尚未有正式模型服務。

## 契約變更流程
1. 修改本檔及對應 JSON Schema／example，註明 API Contract 版本及相容性風險。
2. 增加 request/response 合約測試；必要時使用 JSON Schema Validator 在 CI 完整檢查。
3. 同一 PR 更新後端／前端調用端、`DESIGN.md`，避免各組員私下決定不同欄位命名。
4. `docs/schemas/*.json` 是契約基礎；目前既有欄位仍為規劃草案，不能推論已經有真實服務可呼叫。

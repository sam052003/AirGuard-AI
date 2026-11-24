# W1 官方資料真實驗證與可重現性規範

本檔規定**真實資料**與合成 fixture 如何區分，以及進入 W2 ML 前必須通過的 Gate。依據 [docs/w1-data-integration.md](w1-data-integration.md) 的既有解析器；這裡的條件尚未全部實作。

## 權限與下載
1. 環境部 [API 使用說明](https://data.moenv.gov.tw/paradigm)：自行申請 `MOENV_API_KEY`，僅在本機／部署 Secrets 設定，**不能送到 GitHub、PR 或聊天**。
2. 來源清單：`AQX_P_432` 即時 AQI、`AQX_P_13` 歷史小時值、`AQX_P_488` 歷史 AQI、`AQX_P_07` 測站資訊。每種資料的實際欄位、更新時間及授權須從官方現況核實；不能先假設長期資料都可從一次 API 呼叫取得。
3. 下載時保存 `source_id, source_url, query_params_without_api_key, retrieved_at_utc, sha256, record_count, station_id, min_time, max_time, license_notes, schema_version`。
4. 原始資料保留在**不追蹤 Git 的本機目錄**（例如 `data/raw/`）；若需共享，放合法授權的外部存放位置與可重現下載步驟，不將大量原始資料或憑證放在 Repo。

## 逐時清理與品質表
- 必須保留測站、污染物、單位、觀測／發布／取得時間及時區；`MonitorValue00…23` 的每一個小時不可憑空補缺。
- PM2.5 統一為 μg/m³，單位不明拒絕；`ND`、`--`、空白與負值標 `missing` 或 `invalid`，不補 0。
- 同站同時刻重複紀錄需記錄來源版本及衝突策略，不靜默選最後一筆。
- 產出每站 × 每月：預期時數、實際時槽、有效時數、缺失／異常、coverage、第一／最後觀測時刻、最大連續缺失、是否可訓練；計算方式公開。
- 必須釐清 `observed_at` 與真實 `available_at`。如果無發布時間歷史證據，只能標示**依觀測時間重建的離線回測**，不能稱為嚴格 point-in-time 即時回測。

## W1 → W2 Gate（2026-11-24 真實資料驗證狀態）
- [x] 至少 1 個**臺中市官方測站**的資料來源與身分確認；已由 `AQX_P_07`（SHA256: `4468bf12f298708e97e746dfadd3f819f07f00d0c889450304c17a8e26194494`）與 `AQX_P_432`（SHA256: `9b194fe5ac6980649117299fd6f7aad0e3fd851da2d3bea80570e67b2ce89271`）核實臺中市 6 座官方測站（豐原 `28`、沙鹿 `29`、大里 `30`、忠明 `31`、西屯 `32`、臺灣大道 `88`）之 `TWD97` 座標與行政區資訊。
- [x] 實際下載歷史小時值；已由 `AQX_P_13` 分頁下載（`limit=500, max_pages=2`）取得 2024-03-11～2026-11-23（`Asia/Taipei`）逐時 PM2.5，透過 `--raw-dir data/raw/...` 保存各頁原始回應 bytes 與 `manifest.json`（含 `retrieved_at_utc`、每頁與批次 `sha256`、不含金鑰之查詢參數、官方來源 URL 及政府資料開放授權條款說明），並驗證可由 `--input data/raw/...` 離線重算一致的品質報告（詳見 [docs/w1-data-integration.md](w1-data-integration.md)）。
- [x] 每站／月的樣本量、有效率與缺失統計表，剔除理由可追溯（區分紀錄內 `missing_hours`、未出現之 `unobserved_hours`、`invalid_hours`、上游完全相同重複日紀錄 `duplicate_summary`，並明確區分整月日曆達標 `is_calendar_month_trainable` 與局部視窗達標 `is_window_trainable`：一般站 `28`～`32` 為 31 個整月達標＋2 個首尾非完整邊界月）。
- [x] 確認預測時距 1／3／6h 的有效樣本數；以試點站西屯（`siteid=32`）為例，2024-03-11～2026-11-23 有效觀測 `23,046` 小時，有效預測樣本對數為 `1h=22,849`、`3h=22,797`、`6h=22,745`（只有起點 `t` 與目標 `t+h` 皆為 `quality_flag="ok"` 才計入）。
- [x] 在離線合成資料、失效情境與真實資料上分別跑測試；GitHub 倉庫僅提交**合成 fixture**（`data/fixtures/`）與不含秘密的統計摘要。
- [x] 依時間先後規劃 W2 凍結之 train／validation／test 區間建議（以一般站 `28`～`32` 驗證可得之 2024-03-11～2026-11-23 共 23,712 小時視窗，按時間先後 70%／15%／15% 切分，並標明 `backtest_mode="reconstructed_from_observed_at"`；**W2 模型與 Baseline 尚未執行訓練**）。

## 不可接受的交付
- 直接把合成 `station_id=999` 當官方臺中測站。
- 把沒實際下載的年份、缺值率、MAE、PM2.5 數字寫成完成。
- API 返回 `200` 就認定資料一定為最新、準確、具時序完整性。
- 用單一測站的數值聲稱路段差異或個人吸入量。

驗收記錄請在 PR 中附：執行日期、來源／測站／區間、程式與資料版本、測試命令、匿名化統計、尚未驗證部分。

# W1｜環境部資料接入、品質檢核與真實驗證報告

**範圍**：完成 `AQX_P_07`、`AQX_P_432`、`AQX_P_488`、`AQX_P_13` 四組官方資料集 JSON 解析、逐時長表轉換、分頁擷取、原始回應快照保存與離線 SHA256 重算（`--raw-dir`／`--input`）、缺值／異常／重複值／單位／時區檢查、每站×每月資料品質統計、`.env` 環境變數管理及 19 項離線單元測試，並於本機透過 `MOENV_API_KEY` 完成臺中市 6 座官方測站的真實資料驗證。**GitHub Actions CI 僅執行離線合成 fixture 測試；ChatGPT Reviewer 未獨立持有金鑰執行線上擷取；目前尚未進行 ML 模型訓練、Agent 或 Web 開發。**

## 1. 官方資料集與實測欄位格式

2026-11-24 透過環境部 API v2（`https://data.moenv.gov.tw/api/v2/{DATASET}`）實測確認，當 `format=JSON` 時，API 直接回傳**頂層 JSON 陣列（`list[dict]`）**（本模組同時相容頂層 `list` 與 `{"records": [...]}` 結構），且 `AQX_P_13`、`AQX_P_488` 支援 `filters=siteid,EQ,<站碼>|itemengname,EQ,PM2.5` 伺服器端篩選：

| 資料集 | 官方用途 | 實測關鍵欄位 | 實測發現與處理規則 |
|---|---|---|---|
| [AQX_P_07](https://data.moenv.gov.tw/dataset/detail/AQX_P_07) | 空氣品質監測站基本資料 | `siteid, sitename, siteengname, areaname, county, township, siteaddress, twd97lon, twd97lat, sitetype` | 全臺共 80 站，其中臺中市共 6 站（5 座一般站＋1 座交通站）；座標為 `TWD97` 經緯度，無效或缺失時標示 `null` 與 `coordinate_status=missing` |
| [AQX_P_432](https://data.moenv.gov.tw/dataset/detail/AQX_P_432) | 即時空氣品質指標（AQI） | `siteid, sitename, county, aqi, status, pollutant, pm2.5, pm2.5_avg, publishtime, longitude, latitude` | 全臺共 84 筆；嚴格分離 `official_aqi` 與當小時觀測 `observed_pm25_ug_m3`（`pm2.5`），不將移動平均 `pm2.5_avg` 或 `aqi` 混為逐時 PM2.5 |
| [AQX_P_488](https://data.moenv.gov.tw/dataset/detail/AQX_P_488) | 歷史空氣品質指標（AQI） | `siteid, sitename, county, aqi, status, pollutant, pm2.5, pm2.5_avg, windspeed, winddirec, datacreationdate` | 時間欄位為 `datacreationdate`（`YYYY-MM-DD HH:MM`，`Asia/Taipei`），轉存為 `observed_at_utc`；因無歷史發布延遲紀錄，`published_at_utc` 保持 `null` |
| [AQX_P_13](https://data.moenv.gov.tw/dataset/detail/AQX_P_13) | 空品測站每小時監測資料 | `siteid, sitename, itemid, itemname, itemengname, itemunit, monitordate, monitorvalue00..23` | `PM2.5` 的 `itemid="33"`、`itemunit="μg/m3"`；實測 `monitordate` 帶有尾端空白（如 `"2026-11-23 "`），且上游資料庫在部分月底日期存在 2～4 筆完全相同的重複列 |

## 2. 環境變數與 API Key 管理

1. **設定方式**：將專案根目錄 `.env.example` 複製為 `.env`，並填入 `MOENV_API_KEY`（`.gitignore` 已排除 `.env` 與 `.env.*`）。
2. **載入優先序**：`MOENVClient` 透過 `resolve_api_key()` 依序讀取：
   - 明確傳入的 `api_key` 參數
   - 已存在且非空白的系統環境變數 `MOENV_API_KEY`（優先於 `.env`）
   - 專案根目錄 `.env`（當系統環境變數未設定或為空字串時，自動使用 `python-dotenv` 回退讀取 `.env`，且不污染全域環境變數）
3. **錯誤提示與安全保護**：當系統環境變數與 `.env` 皆缺少有效金鑰時，CLI 會清楚提示如何建立 `.env` 或設定 `$env:MOENV_API_KEY` 並以 exit code `1` 結束，不會直接崩潰或將金鑰輸出至標準輸出、錯誤日誌、原始快照 manifest、測試或例外訊息中。

## 3. Windows PowerShell 安裝、原始快照保存與離線重算指令（優先使用 `py`）

```powershell
# 1. 安裝套件（使用 -c requirements.lock.txt 套用鎖定版本 python-dotenv==1.2.4）
py -m pip install -c requirements.lock.txt -e .

# 2. 執行 19 項離線單元測試（僅使用合成資料與假金鑰，透過 load_dotenv_file=False 或臨時檔隔離本機真實 .env）
py -m unittest discover -s tests -v

# 3. 離線合成資料煙霧測試（站碼 991/992/993/999 均為合成測試值）
py -m airguard --dataset AQX_P_07 --input data/fixtures/aqx_p_07_synthetic.json --county 臺中市
py -m airguard --dataset AQX_P_432 --input data/fixtures/aqx_p_432_synthetic.json
py -m airguard --dataset AQX_P_488 --input data/fixtures/aqx_p_488_synthetic.json
py -m airguard --dataset AQX_P_13 --input data/fixtures/aqx_p_13_synthetic.json

# 4. 線上真實官方資料驗證並將各頁原始回應 bytes 與 manifest.json 保存於 data/raw/（已被 .gitignore 排除，不含 API Key）
py -m airguard --dataset AQX_P_07 --live --county 臺中市 --raw-dir data/raw/aqx_p_07_taichung --output data/normalized/taichung_stations.jsonl --report-output data/normalized/aqx_p_07_taichung_report.json
py -m airguard --dataset AQX_P_432 --live --county 臺中市 --raw-dir data/raw/aqx_p_432_taichung --output data/normalized/taichung_aqi_live.jsonl --report-output data/normalized/aqx_p_432_taichung_report.json
py -m airguard --dataset AQX_P_488 --live --station-id 32 --limit 100 --raw-dir data/raw/aqx_p_488_site32 --output data/normalized/taichung_32_hist_aqi.jsonl --report-output data/normalized/aqx_p_488_site32_report.json
py -m airguard --dataset AQX_P_13 --live --station-id 32 --limit 500 --max-pages 2 --on-duplicate dedup_identical --raw-dir data/raw/aqx_p_13_site32 --output data/normalized/taichung_32_hourly_pm25.jsonl --report-output data/normalized/aqx_p_13_site32_report.json

# 5. 離線快照重算：不需網路連線或 API Key，直接讀取 data/raw/ 下的原始分頁 bytes，逐頁核對 SHA256 並重算完全一致的品質報告
py -m airguard --dataset AQX_P_13 --input data/raw/aqx_p_13_site32 --station-id 32 --on-duplicate dedup_identical --report-output data/normalized/aqx_p_13_site32_replay_report.json
```

### 原始快照目錄格式（`--raw-dir`）
當指定 `--raw-dir data/raw/aqx_p_13_site32` 時，程式會在該目錄下寫入：
- `page_0000_offset_0.json`、`page_0001_offset_500.json`：環境部 API 各分頁回應的**原始未修改 bytes**。
- `manifest.json`：記錄 `source_id`、`source_url`、`query_params_without_api_key`（不含 `api_key`）、`retrieved_at_utc`、整體 `sha256`、`page_sha256s` 與各分頁檔名及筆數。
當後續以 `--input data/raw/aqx_p_13_site32` 離線重跑時，`load_raw_snapshot()` 會逐頁讀取原始 bytes 並重新計算 SHA256，若任何分頁檔案遭竄改或與 `manifest.json` 不符即拋出 `DataError`，確保 2024–2026 品質統計完全可重算。

## 4. 臺中市官方候選監測站清單（`AQX_P_07` 與 `AQX_P_432` 實測核對）

- **擷取時間（UTC）**：`2026-11-24T14:46:24.084738+00:00`（`AQX_P_07`）、`2026-11-24T14:46:25.110971+00:00`（`AQX_P_432`）
- **原始回應 SHA256**：
  - `AQX_P_07`：`4468bf12f298708e97e746dfadd3f819f07f00d0c889450304c17a8e26194494`
  - `AQX_P_432`：`9b194fe5ac6980649117299fd6f7aad0e3fd851da2d3bea80570e67b2ce89271`
  - `AQX_P_488`（`siteid=32`, `limit=100`）：`afec93a44512c166ce8996e4074d60cfc0f16f2b80954fe749cf014f92734d35`

| `station_id` | 站名 | 英文站名 | 行政區 | 站點類型 | TWD97 經度 | TWD97 緯度 | 2026-11-24 22:00 官方 AQI | 當小時觀測 PM2.5 (μg/m³) |
|---|---|---|---|---|---:|---:|---:|---:|
| `28` | 豐原 | Fengyuan | 臺中市豐原區 | 一般站 | 120.74252414 | 24.25699731 | 40 | 10.0 |
| `29` | 沙鹿 | Shalu | 臺中市沙鹿區 | 一般站 | 120.56879400 | 24.22562800 | 52 | 9.0 |
| `30` | 大里 | Dali | 臺中市大里區 | 一般站 | 120.67844444 | 24.09961111 | 39 | 8.0 |
| `31` | 忠明 | Zhongming | 臺中市南屯區 | 一般站 | 120.64109200 | 24.15195800 | 42 | 10.0 |
| `32` | 西屯 | Xitun | 臺中市西屯區 | 一般站 | 120.61691700 | 24.16219700 | 47 | 9.0 |
| `88` | 臺灣大道 | Taiwan Avenue | 臺中市西屯區 | 交通站 | 120.65671110 | 24.15890000 | 59 | 11.0 |

## 5. 臺中市 6 座測站 `AQX_P_13` 逐時 PM2.5 歷史資料盤點總表

使用分頁下載（`limit=500, max_pages=2`，查詢條件 `filters=siteid,EQ,<id>|itemengname,EQ,PM2.5`，重複處理策略 `--on-duplicate dedup_identical`）實測結果如下：

| `station_id` | 站名 | 可得日期範圍（Asia/Taipei） | 涵蓋月份（整月達標／局部視窗達標） | 預期視窗時數 | 實際取得時槽 | 有效時數 (`ok`) | 紀錄缺值 (`missing`) | 視窗未觀測時數 | 異常時數 (`invalid`) | 視窗完整率 (`window_coverage`) | 最大連續缺失 | 1h 有效樣本對 | 3h 有效樣本對 | 6h 有效樣本對 | 批次 SHA256（前 16 碼） |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `28` | 豐原 | 2024-03-11～2026-11-23 | 33 (31 整月 + 2 局部) | 23,712 | 23,496 | 23,162 | 334 | 216 | 0 | 97.68% | 73h | 22,983 | 22,932 | 22,873 | `c476aafe4e7c1ab4` |
| `29` | 沙鹿 | 2024-03-11～2026-11-23 | 33 (31 整月 + 2 局部) | 23,712 | 23,496 | 23,135 | 361 | 216 | 0 | 97.57% | 90h | 22,946 | 22,906 | 22,866 | `bb531344c5e92a42` |
| `30` | 大里 | 2024-03-11～2026-11-23 | 33 (31 整月 + 2 局部) | 23,712 | 23,496 | 23,027 | 469 | 216 | 0 | 97.11% | 75h | 22,822 | 22,750 | 22,688 | `baf0b40a5ad283bd` |
| `31` | 忠明 | 2024-03-11～2026-11-23 | 33 (31 整月 + 2 局部) | 23,712 | 23,496 | 23,214 | 282 | 216 | 0 | 97.90% | 96h | 23,042 | 23,004 | 22,971 | `b83c5f8f99eebff2` |
| `32` | 西屯 | 2024-03-11～2026-11-23 | 33 (31 整月 + 2 局部) | 23,712 | 23,496 | 23,046 | 450 | 216 | 0 | 97.19% | 99h | 22,849 | 22,797 | 22,745 | `68e8247f2f3745be` |
| `88` | 臺灣大道 | 2026-01-02～2026-11-23 | 11 (10 整月 + 1 局部) | 7,824 | 7,680 | 7,471 | 209 | 144 | 0 | 95.49% | 77h | 7,401 | 7,369 | 7,326 | `7d7963be02125c3a` |

- **完整 SHA256 對照**：
  - `28`（豐原）：`c476aafe4e7c1ab4c198cdb5e8a469faf039e8a920afd551b1d3489b6bb843d8`（Page 0: `18b640e649eab2d48b8252fb2963131000556a3a52ba77357a4f3a622135cb40`；Page 1: `76406284da12c8dc4c244aeef36de6f46e8f04f3cdf34ebb773bb3a0b7a90b8b`）
  - `29`（沙鹿）：`bb531344c5e92a428079c9e86558ae7189ca878c05f6ed1d866b9b99440c0662`（Page 0: `ea63260cec76ced12ad554b537fb2eb4026246db449bb85d4a21251b60191c48`；Page 1: `2618512008915e7235c7f99e69104f8cfbd12ce1b59948fe8294301077aacf69`）
  - `30`（大里）：`baf0b40a5ad283bd0a5d34d8e1909e9b07ce2a4a8d66ba76dce2288cf673ee68`（Page 0: `48b04ebdabd443a3263f3f5f48baccf622d2985bba8c5e3c3b3b2a919074112c`；Page 1: `34e7ef123e9797c3d499f082a48e49b376def1cff5bf91baf5434fbbb1e0cfd4`）
  - `31`（忠明）：`b83c5f8f99eebff2cb8282f2840bc4473ce97cb58df251f98bca1c8849fa9fb8`（Page 0: `8d627d378e2c36c0a4bda92d3f0783c3eb574d95069a157816ef657bb30a401e`；Page 1: `a224d5c6af531b1be1948816c813051896dabe02ea536f65937c775c85f9ea63`）
  - `32`（西屯）：`68e8247f2f3745bedbf30eb46e17755056dee23c08de77e9e0df50612de4c213`（Page 0: `79ccfac920e8c5628b6280df5f9804b09777a6ec41580359790b8925de904c84`；Page 1: `7d71735b8792b6d571eb4a414a3079afdf473c78d1b9bce5829029c0ad133bf8`）
  - `88`（臺灣大道）：`7d7963be02125c3a70faf8b68ce3e867389c25b0c1bbc13cde7570773f059dcd`

## 6. 試點測站（西屯站 `siteid=32`）逐月資料品質表（2025-11～2026-11 摘錄，共 33 個月）

完整 33 個月（`2024-03`～`2026-11`）皆可由 `py -m airguard --dataset AQX_P_13 --live --station-id 32 --limit 500 --max-pages 2 --on-duplicate dedup_identical` 重現；以下列出最近 13 個月份明細：

| 月份 (`Asia/Taipei`) | 日曆月預期時數 | 觀測視窗預期時數 | 實際時槽 | 有效時數 (`ok`) | 缺值時數 (`missing`) | 視窗未觀測時數 | 日曆月完整率 (`calendar_coverage`) | 視窗完整率 (`window_coverage`) | 最大連續缺失 | 1h 有效對 | 3h 有效對 | 6h 有效對 | 可訓練 (`is_trainable`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `2025-11` | 720 | 720 | 720 | 715 | 5 | 0 | 99.31% | 99.31% | 1h | 710 | 710 | 710 | `true` |
| `2025-12` | 744 | 744 | 744 | 737 | 7 | 0 | 99.06% | 99.06% | 2h | 731 | 730 | 730 | `true` |
| `2026-01` | 744 | 744 | 744 | 738 | 6 | 0 | 99.19% | 99.19% | 2h | 733 | 732 | 732 | `true` |
| `2026-02` | 672 | 672 | 672 | 667 | 5 | 0 | 99.26% | 99.26% | 1h | 662 | 662 | 662 | `true` |
| `2026-03` | 744 | 744 | 744 | 739 | 5 | 0 | 99.33% | 99.33% | 1h | 734 | 734 | 734 | `true` |
| `2026-04` | 720 | 720 | 720 | 715 | 5 | 0 | 99.31% | 99.31% | 1h | 710 | 710 | 710 | `true` |
| `2026-05` | 744 | 744 | 720 | 713 | 7 | 24 | 95.83% | 95.83% | 24h | 704 | 700 | 694 | `true` |
| `2026-06` | 720 | 696 | 672 | 669 | 3 | 24 | 92.92% | 96.12% | 24h | 665 | 663 | 660 | `true` |
| `2026-07` | 744 | 744 | 720 | 702 | 18 | 24 | 94.35% | 94.35% | 24h | 696 | 692 | 686 | `true` |
| `2026-08` | 744 | 744 | 744 | 654 | 90 | 0 | 87.90% | 87.90% | 85h | 649 | 649 | 649 | `true` |
| `2026-09` | 720 | 720 | 720 | 717 | 3 | 0 | 99.58% | 99.58% | 1h | 714 | 714 | 714 | `true` |
| `2026-10` | 744 | 744 | 744 | 740 | 4 | 0 | 99.46% | 99.46% | 1h | 736 | 736 | 736 | `true`（整月達標） |
| `2026-11` | 720 | 552 | 552 | 548 | 4 | 0 | 76.11% | 99.28% | 1h | 543 | 542 | 538 | `is_window_trainable=true` / `is_calendar_month_trainable=false` |

> 註：品質報告明確區分 `is_calendar_month_trainable`（整月日曆完整率 `calendar_coverage >= 80%` 且 `valid_hours >= 336`）與 `is_window_trainable`（已取得片段視窗完整率 `window_coverage >= 80%` 且 `valid_hours >= 336`）。西屯站 33 個涵蓋月份中，有 **31 個整月日曆達標月份**（`2024-04`～`2026-10`），而首月 `2024-03`（`2024-03-11` 起，504 小時視窗，`calendar_coverage=67.20%`、`window_coverage=99.21%`）與當月 `2026-11`（截至 `2026-11-23`，552 小時視窗，`calendar_coverage=76.11%`、`window_coverage=99.28%`）為**首尾非完整邊界月**（僅局部視窗達標，不計入整月完整月份）。

## 7. 已驗證的資料限制與風險（W1 實測紀錄）

1. **上游重複日紀錄**：`AQX_P_13` 在部分日期（例如 `2026-01-31`、`2026-02-28`、`2026-03-31`、`2026-04-12`、`2026-09-26..30` 等，一般站前 1,000 筆中含有 21 筆重複日，共 504 個小時槽位）存在完全相同的重複 JSON 物件。預設 `on_duplicate="error"` 會嚴格阻擋；批次清洗使用 `on_duplicate="dedup_identical"` 僅在 24 小時數值與品質旗標完全一致時去重並寫入 `duplicate_summary`（實測 `conflict_flagged_invalid = 0`），若出現數值衝突仍會拋出 `DataError`。若使用 `on_duplicate="flag_conflict"`，則會先將衝突前的原始數值與品質旗標記錄至 `duplicate_log`（`previous_value_ug_m3`、`conflicting_value_ug_m3`），再將該時槽設為 `null` 與 `invalid`。
2. **整日未出現在 API 回應的缺漏日**：在 `2024-03-11`～`2026-11-23`（共 988 個日曆日）中，各一般站實際含 979 個不重複日期，有 9 個日曆日（216 小時，如 `2026-05`、`2026-06`、`2026-07` 各缺 1 日）未出現在 `AQX_P_13` 回應中。`station_month_quality_report` 將其明確計入 `unobserved_hours` 與 `max_consecutive_missing_hours`（≥24h），絕不自動內插或補 0。
3. **極端 PM2.5 異常值門檻依據與可配置性**：依據[環境部空氣品質指標（AQI）計算方式說明](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx)，PM2.5 最高分級（AQI 500）之濃度上限為 `500.4 μg/m³`，而環境部自動監測站 β 射線法／FEM 儀器之小時濃度物理量測上限通常為 `1000 μg/m³`。因此程式預設以 `MAX_VALID_PM25_UG_M3 = 1000.0` 作為儀器／傳輸異常值（`quality_flag="invalid"`）門檻，並於 CLI 提供 `--max-pm25` 與函式參數 `max_valid_pm25_ug_m3`（亦可設為 `None` 停用上限裁切），同時記錄於品質報告 `qc_thresholds` 中，避免未經說明地截斷極端污染事件。
4. **API 分頁與 `filters` 掃描上限**：`AQX_P_13` 未加 `filters` 時，單日全臺約 80 站 × 18 測項 ≈ 1,440 筆；加上 `filters=siteid,EQ,32|itemengname,EQ,PM2.5` 後，前兩頁（`offset=0, limit=500` 與 `offset=500, limit=500`，合計 1,000 筆日紀錄）可在約 1.3 秒內取回約 2.7 年逐時資料。但當 `offset >= 1000` 搭配 `filters` 時，環境部後端資料庫因全表掃描逾時（>20 秒）。因此 API 線上分頁適合取得近 1,000 筆日紀錄（約 33 個月），更早期歷史資料應搭配官方按月歷史檔匯入離線 `--input` 流程。
5. **回測時間語意與驗證邊界**：`AQX_P_13` 與 `AQX_P_488` 僅提供觀測時刻（`MonitorDate`＋小時、`DataCreationDate`），未提供歷史每筆資料當下的實際發布延遲時間戳（`published_at_utc=null`）。因此後續 W2 歷史回測在報告中一律標記為 `reconstructed_from_observed_at`（依觀測時間重建之離線回測），不得宣稱為嚴格 point-in-time 即時發布回測。此外，本報告中之臺中 6 站統計與 SHA256 為本機持有 `MOENV_API_KEY` 之實測紀錄（可透過本機 `--raw-dir` 保存之原始快照以 `--input` 離線重算驗證）；GitHub CI 僅驗證合成資料。

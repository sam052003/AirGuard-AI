# W1｜環境部資料接入與品質檢核（初版）

**範圍**：實作官方資料 JSON 解析、逐時長表轉換、缺值與單位檢查、唯讀 API 客戶端及離線單元測試。尚未完成實際歷史下載、站點／月份涵蓋盤點或 ML 訓練，不把合成測試資料寫成真實測站觀測。

## 官方來源

- [AQX_P_432](https://data.moenv.gov.tw/dataset/detail/AQX_P_432)：官方每小時 AQI；`AQI` 與 `PM2.5` 分別保存。
- [AQX_P_13](https://data.moenv.gov.tw/dataset/detail/AQX_P_13)：`MonitorDate` 與 `MonitorValue00`～`MonitorValue23`，轉為每筆測站／小時資料。
- [AQX_P_488](https://data.moenv.gov.tw/dataset/detail/AQX_P_488)：歷史 AQI；尚未接入長期下載流程。
- [AQX_P_07](https://data.moenv.gov.tw/dataset/detail/AQX_P_07)：測站基本資訊；地理欄位整合待後續進行。
- [API 官方說明](https://data.moenv.gov.tw/paradigm)：會員 API 金鑰必須放在伺服器環境變數。

## 安裝與離線重現

環境需求 Python 3.10+（建議建立虛擬環境），從專案根目錄執行：

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m airguard --dataset AQX_P_13 --input data/fixtures/aqx_p_13_synthetic.json --output data/normalized/hourly_sample.jsonl
python -m airguard --dataset AQX_P_432 --input data/fixtures/aqx_p_432_synthetic.json
```

上述 JSON 的站點代碼 999 與量測數值均為**合成測試資料**。輸出資料不具現實空氣品質意義。

## 官方 API 連接（需自行申請金鑰）

使用環境變數 `MOENV_API_KEY`（不可寫入程式碼或 Commit），例如 PowerShell：

```powershell
$env:MOENV_API_KEY = "在環境部取得的金鑰"
python -m airguard --dataset AQX_P_432 --live --output data/normalized/aqi_live.jsonl
```

`AQX_P_13` 也可使用 `--live`；此命令目前僅請求**單頁最多 1000 筆**，不是完整歷史資料下載。正式訓練需另做分頁／歷史檔盤點並保存時間、站點、檔案雜湊及資料授權資訊；執行時會顯示 live 模式，但不代表資料時效已合格，必須依 `published_at_utc` 另外判斷。

## 品質與安全規則

- 缺值（空白、`--`、`ND`）保留為 JSON `null` 和 `quality_flag=missing`；非數值或負數標記 `invalid`。
- 僅選取 PM2.5，拒絕單位不符；同一測站同一小時重複則拒絕處理，避免未審查的覆蓋。
- 時間以臺灣時間解析，再存為 UTC ISO 8601；發布時間未知就保留 `null`，不能用擷取時間替代。
- 目前不會推論街道級污染、個人真實暴露或未來 AQI；API 異常不會顯示金鑰。

## 下一步驗收 Gate

1. 使用真實 API 金鑰或合法下載檔，確認大小寫、欄位與分頁的實際格式。
2. 取得臺中候選測站資料，統計各月缺值率、有效時數、時間連續性及資料發布延遲。
3. 保存資料來源、擷取時間與版本快照後，才啟動 Persistence Baseline 和 1／3／6 小時時序回測。

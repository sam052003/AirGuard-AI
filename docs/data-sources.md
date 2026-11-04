# 官方資料來源與資料品質規格

本文件以 AirGuard AI 提案內容作為資料契約起點。尚未完成完整歷史資料下載與測站品質盤點。

| ID | 官方來源 | 用途 | 資料型態與注意事項 |
| --- | --- | --- | --- |
| `AQX_P_432` | [每小時 AQI](https://data.moenv.gov.tw/dataset/detail/AQX_P_432) | 顯示官方 AQI、污染物與發布時間 | `siteid`, `aqi`, `pm2.5`, `publishtime` 等欄位須依實際 API schema 驗證 |
| `AQX_P_488` | [歷史 AQI](https://data.moenv.gov.tw/dataset/detail/AQX_P_488) | 歷史分析與輔助回測 | 月份下載及欄位內容依取得檔案核對 |
| `AQX_P_13` | [小時值資料](https://data.moenv.gov.tw/dataset/detail/AQX_P_13) | 逐小時 PM2.5 目標資料 | `MonitorValue00…23` 的寬表欄位應正規化成長表，確認時間與單位 |
| `MOENV_AQI_GUIDE` | [AQI 活動指引](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx) | 規則與敏感族群建議 | 保存版本、生效日期與適用條件；不直接把 PM2.5 預測換算成官方 AQI |

## 取得與驗證

1. 保存來源網址、查詢條件、擷取時間、HTTP／資料狀態與 SHA-256；不得公開 API 金鑰。
2. 建立欄位映射與單位檢查，所有 PM2.5 模型目標為 μg/m³。
3. 儲存測站 ID、觀測時間、資料發布時間（可得時）、擷取時間及來源版本。
4. 將過期、缺值、異常及重複另行記錄，處理後仍保留原始資料及排除理由。
5. 每個回測 fold 僅使用預測起點之前可取得的歷史觀測；歷史真正可得時間未知時，須披露為重建回測。
6. 預先產生站點 × 月份的有效樣本數、缺失率與時間連續性報告，再確定首批臺中測站及資料區間。

## 研究限制

- 2024–2026 為提案候選期間，實際完整度、保留區間及官方 API 額度需要實作驗證。
- 測站觀測值不能外推為特定街道或個人暴露。
- 官方 AQI 是多污染物及不同平均時間規則下的發布指標，與單一時點 PM2.5 觀測或模型預測不同。

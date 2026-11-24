# 官方資料來源、欄位與使用限制

| 代碼 | 來源 | 重要欄位 | 使用方式 |
|---|---|---|---|
| AQX_P_432 | [官方每小時 AQI](https://data.moenv.gov.tw/dataset/detail/AQX_P_432) | SiteId、SiteName、AQI、PM2.5、publishtime、Longitude／Latitude | 取得目前正式發布的 AQI 與測站濃度 |
| AQX_P_488 | [歷史 AQI](https://data.moenv.gov.tw/dataset/detail/AQX_P_488) | SiteId、DataCreationDate、PM2.5、WindSpeed 等 | 按月官方歷史下載，檢查可用年份 |
| AQX_P_13 | [逐時污染物](https://data.moenv.gov.tw/dataset/detail/AQX_P_13) | SiteId、ItemName、ItemUnit、MonitorDate、MonitorValue00…23 | 逐時 PM2.5 模型候選主資料 |
| AQX_P_07 | [測站基本資料](https://data.moenv.gov.tw/dataset/detail/AQX_P_07) | SiteId、SiteName、County、TWD97Lon／Lat | 地圖座標與標準測站識別 |
| MOENV AQI RULE | [AQI 健康影響](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx) | AQI 各級、族群活動建議 | 版本化決策規則 |

## 存取與工程限制

- 官方 [API 使用說明](https://data.moenv.gov.tw/paradigm) 明示**會員 API Key**。團隊應由 Server Side 使用金鑰、遵守官方存取條款及頻率；不要 Push `.env` 或 API Key。
- 先用官方提供的歷史 CSV／JSON 檔盤點站點 × 月份，確認真正可下載範圍；**文件列有資料集不等於已取得完整 2024–2026 訓練資料**。
- `MonitorValue00…23` 欄位轉為 24 個以小時計的觀測，保留原始測站、日期、測項、單位與缺漏旗標。
- 採用同一模型標的「**原始逐時 PM2.5**」（μg/m³），不要把 `PM2.5_AVG` 不同移動平均窗當成同一目標。
- `observed_at`、`published_at`、`retrieved_at` 三種時間分開記錄；`published_at` 缺失則標未知，回測說明是否為嚴格歷史可用性評估。
- 上線時有 API 故障或逾期，顯示已驗證快取與**快取日期**，不顯示「最新 AQI」。
- 外部氣象資料非最低必做前置；使用中央氣象署 API 會另外需要授權碼及測站／時區對齊。[CWA API 說明](https://opendata.cwa.gov.tw/devManual/description)。

## 已確認不能由官方測站資料直接支援的主張

AQX_P_432、488、13 與 07 **不能單獨提供道路逐段／逐分鐘 PM2.5 真值**，不得因此繪製低污染街道路線熱點，也不把站點值等同個人實測暴露。

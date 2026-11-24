# AirGuard AI｜公開資料可實作性審查（2026-11-24）

## 審查結論

**最低可展示系統**：環境部官方 AQI、測站地圖、PM2.5 歷史與 1／3／6h 預測、官方活動規則、工具導向 Agent、6h 內活動時段比較、測站濃度×時間估算及完整來源／誤差／安全降級。

此結論是**「有公開資料和成熟技術可合理實作」**，不是 API Key 已取得、訓練資料已全數下載、模型已驗證或網站已上線。

## 官方資源核對

| ID | 官方資料與欄位 | 可合理支援 | 工程風險 |
|---|---|---|---|
| R1 | [AQX_P_432](https://data.moenv.gov.tw/dataset/detail/AQX_P_432)：站點、AQI、PM2.5、發布時間 | 正式目前 AQI 與污染物卡 | 每小時發布非零延遲；API Key、缺值、限額 |
| R2 | [AQX_P_488](https://data.moenv.gov.tw/dataset/detail/AQX_P_488)：月別歷史 AQI、站點、PM2.5、風速 | 歷史趨勢、延伸特徵 | 可下載年份、不同版次與完整度需實際盤點 |
| R3 | [AQX_P_13](https://data.moenv.gov.tw/dataset/detail/AQX_P_13)：MonitorDate＋Value00…23 | 小時 PM2.5 時序、ML 訓練 | 寬表轉長表；資料分佈、缺值、測站變更 |
| R4 | [AQX_P_07](https://data.moenv.gov.tw/dataset/detail/AQX_P_07)：測站座標及站名 | 測站地圖、站點選擇 | 測站位置≠道路污染真值 |
| R5 | [環境部 AQI 指引](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx) | AQI 分級與活動建議 | 需正確區分族群、官方指引版本與時效 |
| R6 | [MOENV API 說明](https://data.moenv.gov.tw/paradigm) | 可由 Backend 透過 Key 取資料 | **需會員 API Key**；不可在前端公開 |
| R7 | [CWA API 說明](https://opendata.cwa.gov.tw/devManual/description) | 可以取得外部氣象欄位（非必需） | 另需授權碼與測站、時間對齊，因此列延伸 |

## 功能分級理由

| 功能 | 分級 | 判斷理由 |
|---|---|---|
| 官方即時／歷史／測站地圖 | P0 | 官方可用來源明確 |
| PM2.5 1、3、6h | P0 | 有逐時資料、可用成熟 ML；**準確率仍待回測** |
| Tool Calling 與官方規則 | P0 | 由團隊自行開發、可用固定案例測試 |
| 6h 時段比較 | P0 | 僅在受模型時距與品質支援時提供條件式結論 |
| 濃度×時間指數 | P0 | 可由合法時間窗濃度與時長直接計算；**不等於個人實際吸入量** |
| SHAP 與已記錄活動加總 | P1 | 具成熟演算法與算式，但須先完成模型及資料契約 |
| 官方多日預報 | 參考／延伸 | 官方存在區域性預報，**不能冒充自建測站 6h 精確模型** |
| 路線低暴露排名／路段熱點 | 排除 | 現存測站點位未證明道路級濃度、路段行進時刻與獨立驗證 |
| 健康診斷／保證降低暴露 | 排除 | 不能從資料與特徵解釋推出臨床結論 |

## 建議使用的研究背景數據

- WHO：2019 年室外空污全球估計 420 萬過早死亡（[事實表](https://www.who.int/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health)）。
- MOENV：2019→2025 年 PM2.5 年均 16.2→12.8 μg/m³，約改善 21%，為全國年均而非使用者特定站點（[公告](https://enews.moenv.gov.tw/moenv-news/zh-tw/News/1844)）。
- 2025 年手動測站 PM2.5 年均約 12.8 μg/m³（[環境部說明](https://www.moenv.gov.tw/en/env-affairs/atmospheric-environment/air-quality/air-quality-management/2673.html)）。

不得以這些官方背景統計替代本組的 ML、Agent 或活動估算實測結果。

## 實作前必須自行驗證的四件事

1. 申請並測試 MOENV API Key；核對當前回應 JSON Schema、權限與配額。
2. 確認 AQX_P_13／AQX_P_488 指定年度及臺中測站的可下載日期、有效小時數與缺值情況。
3. 鎖定至少一個可回測測站、時間分割、來源版本與模型特徵取得時間。
4. 針對官方 AQI 規則、超時距、API 失效、不同時間平均窗與空間尺度執行失效測試。

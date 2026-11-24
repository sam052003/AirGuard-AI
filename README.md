# AirGuard AI｜智慧空氣品質預測與生活決策代理人

**物聯網數據分析與應用（AIoT-DA）｜三人團體期末專題**  
**研究與設計修訂：2026-11-24｜版本：v3（依公開資料重新收斂可實作範圍）**

> **專案目前屬設計與提案階段。** 本 README 描述**計畫實作的功能**，不表示已完成 Web、ML、Agent 或任何實驗數據。原始已繳交的 Word／PPTX 保留於 `docs/proposal/`；新版另存檔案，不覆蓋原始歷史記錄。

## 1. 專題定位

AirGuard AI 將環境部的**官方 AQI 與歷史每小時 PM2.5**、短期 ML 預測、官方活動建議及可追溯的 AI Agent 整合成情境式決策服務。主要使用情境是：「我接下來幾小時想慢跑 40 分鐘，哪個時段較值得考慮？依據是什麼？」

系統**只在有充分證據的測站尺度**提供比較；不將道路、巷弄或個人吸入量假裝已被官方測得。

### 研究背景（外部統計，非系統成果）

- WHO 估計全球 **2019 年**室外空污造成約 **420 萬人過早死亡**。[來源](https://www.who.int/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health)
- 環境部公布臺灣 PM2.5 年平均濃度由 **2019 年 16.2** 降至 **2025 年 12.8 μg/m³**，約改善 21%；須注意手動／自動監測口徑不同。[來源](https://enews.moenv.gov.tw/moenv-news/zh-tw/News/1844)
- 官方 AQI 由多種污染物及不同平均窗組成，**不等於模型預測的單一 PM2.5 濃度**。[官方指引](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx)

## 2. 核心功能與範圍

| 分級 | 功能 | 交付界線 |
|---|---|---|
| **P0 必做** | 官方 AQI／測站地圖／歷史資料、資料品質、PM2.5 1／3／6h ML、活動指引 | 環境部資料＋正確時間戳與來源 |
| **P0 必做** | Agent Tool Calling、活動時段比較、Web Dashboard、來源卡、錯誤降級 | 至少 30 個 Agent 情境驗收 |
| **P0 必做** | **測站尺度**活動濃度×時間估算、ML 與 Agent 雙軌評估 | 單位 μg·h/m³，非個人實測吸入量 |
| **P1 可選** | SHAP 可解釋性、手動活動記錄與估算累積值 | 完成 P0 後加入；缺資料不得以 0 補 |
| **明確排除** | 道路級污染熱點、可靠低污染導航／改道排序、真實個人吸入劑量 | 現有官方測站資料不能支撐道路級可信結論 |

**P1 是有公開方法可實作的擴充，不是本次最低驗收阻擋項**。詳見 [新版 SRS](docs/requirements.md) 與 [可行性審查](docs/feasibility-audit.md)。

## 3. 官方資料與取得限制

| 資料 | 來源 | 用途 |
|---|---|---|
| 即時 AQI | [AQX_P_432](https://data.moenv.gov.tw/dataset/detail/AQX_P_432) | 每小時 AQI、污染物與發布時間 |
| 歷史 AQI | [AQX_P_488](https://data.moenv.gov.tw/dataset/detail/AQX_P_488) | 按月歷史下載、趨勢與對照 |
| 逐時污染物 | [AQX_P_13](https://data.moenv.gov.tw/dataset/detail/AQX_P_13) | PM2.5 建模主資料，00–23 小時寬表轉長表 |
| 測站地理 | [AQX_P_07](https://data.moenv.gov.tw/dataset/detail/AQX_P_07) | 座標、測站地址與基本資料 |
| AQI 健康活動建議 | [官方指引](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx) | Domain Rules 的唯一正式版本依據 |

**API 接入注意**：環境部 API 需要會員 API Key，請先申請並放在本機 `.env` 或部署秘密變數，**不要 Commit 到 GitHub**。歷史公開資料可按官方提供方式下載，快取與 Demo 必須標明資料時間，不宣稱快取是即時資料。[API 說明](https://data.moenv.gov.tw/paradigm)

## 4. 系統架構

```text
① Web UI／站點地圖 → ② Query Interpreter → ③ 受限 Planner Agent
  → ④ 資料取得與品質檢查 → ⑤ ML／分析／暴露估算
  → ⑥ 官方 Domain Rules → ⑦ 時段決策／保守排名 → ⑧ 圖表／引用／稽核
```

LLM 解析情境與呼叫白名單工具，**數值運算、模型推論、官方活動規則判定必須由確定性程式執行**。模型只有測站 **PM2.5 1、3、6 小時**預測，不產生官方未來 AQI。

## 5. 實驗規劃

- **Track A（ML）**：Persistence、Seasonal Naive vs Ridge／Random Forest／XGBoost；按時間 70／15／15＋Rolling-origin；MAE、RMSE、Skill Score，分時距與測站分析。
- **Track B（Agent／決策）**：≥30 固定情境；工具選擇正確率、來源完整率、官方規則一致率、安全降級率、P50／P95 延遲。
- **估算指數單元測試**：計算 `Σ(濃度 μg/m³ × 時長 h)` 的結果、單位與未知區間；不評估個人醫療安全性。

**沒有訓練完成的模型或實驗結果時，所有數字都應維持「待實測」。**

## 6. 四項 Proposal 交付與歷史版本

| 交付項目 | 既有繳交版 | 最新可行性修訂 |
|---|---|---|
| ① Proposal Document | [原始 Word](docs/proposal/AirGuard_AI_Final_Proposal.docx) | [v3 Word](docs/proposal/AirGuard_AI_Proposal_Feasible_v3.docx) |
| ② Proposal Presentation | [原始簡報](docs/proposal/AirGuard_AI_Final_Proposal_Presentation.pptx) | [v3 簡報](docs/proposal/AirGuard_AI_Proposal_Presentation_Feasible_v3.pptx) |
| ③ GitHub Repository | [本倉庫](https://github.com/sam052003/AirGuard-AI) | 本 README 與資料來源／評估／需求規格 |
| ④ DESIGN.md | Git 歷史版本 | [最新 DESIGN](DESIGN.md) |

三人團體專題**暫不規劃組員分工**；各人姓名／學號請依正式資料填寫，避免誤用舊版上傳內容。

## 7. 文件導覽與目前狀態

- [DESIGN.md](DESIGN.md) — 八模組、資料流、AI Agent、ML、API 與安全條件。
- [可實作性審查](docs/feasibility-audit.md) — 逐項判斷公開資料是否足以支援。
- [需求與驗收規格](docs/requirements.md) — FR-01～FR-12、P0／P1／排除範圍。
- [官方資料來源](docs/data-sources.md) — 欄位、授權碼、下載與可靠性風險。
- [實驗計畫](docs/evaluation-plan.md) 與 [開發路線圖](docs/implementation-roadmap.md)。
- [版本變更記錄](docs/decisions/2026-11-24-scope-decision.md) — 說明為何取消路線導航必做承諾。
- [myplan 文件索引](myplan/README.md) — 後續原始摘要與研究需求的重新整合。

**目前狀態**：文件更新完成 ≠ 系統程式／模型／Demo 已完成。資料實際可下載時間涵蓋、歷史缺值與 API 限額仍需在工程階段進一步盤點。
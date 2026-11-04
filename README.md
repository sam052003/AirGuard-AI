# AirGuard AI — 智慧空氣品質預測與生活決策代理人

**AirGuard AI** 是《物聯網數據分析與應用》的**團體期末專題**，結合臺灣環境部公開空氣品質資料、短期 PM2.5 預測、工具導向 AI Agent 與官方 AQI 活動指引，協助使用者比較戶外活動時段、理解污染風險及查看分析依據。

> **專案階段：提案文件已完成，系統實作與實驗尚未進行。** 本倉庫提供一致的技術設計、正式提案、資料來源與評估規格；目前不宣稱已有可執行網站、已訓練模型或測試成績。

## GitHub 專案簡介

**建議的 GitHub Description：** 智慧空氣品質預測與生活決策 AI Agent｜整合環境部開放資料、PM2.5 短期預測與 AQI 活動指引

**建議的 GitHub Topics：** `air-quality`、`pm25`、`ai-agent`、`machine-learning`、`data-analytics`、`taiwan`（Topics 為 GitHub 技術索引標籤，保留英文較容易被搜尋）。

## 團體專題與 Proposal 交付項目

本專題由 **3 位組員共同完成**。目前以課程 Proposal 階段的**四項交付物**為主。

| 課程要求 | 本倉庫對應內容 | 目前狀態 |
| --- | --- | --- |
| ① Proposal Document（提案報告書） | [`docs/proposal/AirGuard_AI_Final_Proposal.docx`](docs/proposal/AirGuard_AI_Final_Proposal.docx) | 文件已備妥 |
| ② Proposal Presentation（提案簡報） | [`docs/proposal/AirGuard_AI_Final_Proposal_Presentation.pptx`](docs/proposal/AirGuard_AI_Final_Proposal_Presentation.pptx) | 文件已備妥 |
| ③ GitHub Repository | 本儲存庫及 `README.md`、提案附件 | **檔案已備妥；建立並 Push 遠端倉庫後完成** |
| ④ `DESIGN.md` | [`DESIGN.md`](DESIGN.md) | 系統提案設計已備妥 |

此階段**不要求已完成 ML 訓練、網站部署或最終實驗**。系統程式與結果將依提案內容於後續階段實作及驗證。

## 專題目標

- **資料取得**：整合官方即時 AQI、歷史 AQI 及逐小時污染物觀測資料，追蹤測站、時間、版本、缺失與資料新鮮度。
- **資料分析與機器學習（ML）**：預測未來 **1、3、6 小時 PM2.5 濃度**（μg/m³），比較 Persistence、Seasonal Naive、Ridge、Random Forest、XGBoost。
- **領域知識**：依官方 AQI 規範與一般／敏感族群活動建議產生可查證的解釋；**模型 PM2.5 預測不等於官方 AQI 預報**。
- **AI Agent 與決策支援**：理解查詢情境、選擇合法工具、驗證資料、比較可支持的候選時段，並提供來源、限制與安全降級說明。
- **實驗評估**：獨立評估模型 MAE/RMSE 與 Agent 工具正確性、來源完整率、規則一致性及異常處理。

## 預期使用情境

使用者問：「我想在臺中安排 40 分鐘的戶外慢跑，接下來幾個小時哪個時段比較合適？」

系統規劃依序完成：解析活動與時段 → 選定有效監測站 → 取得官方 AQI 與 PM2.5 資料 → 檢查資料品質 → 預測短期 PM2.5 → 套用官方活動建議 → 比較可支持的候選時段 → 回覆來源、時間及不確定性。

只有處於模型 **1–6 小時預測範圍**內、且資料品質合格的候選時段才進行模型支持的短期比較。超出範圍的查詢不以 6 小時模型冒充隔日預測，應明示限制或另採具來源且明確標示的官方較長期資訊。

## 文件導覽

| 檔案 | 內容 |
| --- | --- |
| [GitHub 協作注意事項](CONTRIBUTING.md) | 版本管理、文件同步與資料保護（非本次四項必要繳交物） |
| [DESIGN.md](DESIGN.md) | 正式系統設計：架構、模組、資料流、模型、Agent、規則、可行性、評估與限制 |
| [正式提案報告書](docs/proposal/AirGuard_AI_Final_Proposal.docx) | 正式提案報告書 |
| [正式提案簡報](docs/proposal/AirGuard_AI_Final_Proposal_Presentation.pptx) | 正式提案簡報（24 頁） |
| [官方資料來源](docs/data-sources.md) | 官方資料來源、欄位、品質與版控原則 |
| [實驗與評估規劃](docs/evaluation-plan.md) | ML／Agent 雙軌實驗設計、基線與指標 |
| [系統架構圖](docs/architecture.mmd) | Mermaid 系統架構原始圖 |
| [Agent 流程圖](docs/agent-flowchart.mmd) | Mermaid Agent 流程原始圖 |
| [實作時程與里程碑](docs/implementation-roadmap.md) | 專題實作順序與驗收證據 |
| [GitHub 發布指引](docs/github-publishing.md) | 建立遠端倉庫與發布檢查 |

## 初始儲存庫結構

```text
AirGuard-AI/
├── README.md
├── DESIGN.md
├── CONTRIBUTING.md           # GitHub 協作注意事項（補充文件）
├── .gitignore
├── .env.example
├── docs/
│   ├── proposal/                 # 正式提案報告書／簡報
│   ├── architecture.mmd
│   ├── agent-flowchart.mmd
│   ├── data-sources.md
│   ├── evaluation-plan.md
│   ├── implementation-roadmap.md
│   └── schemas/                  # API 輸入輸出設計契約
├── src/                           # 後續 Python 資料、Agent、ML 服務
├── app/                           # 後續 Web 使用者介面
├── data/                          # 資料使用與重現規範（不含原始大檔）
├── experiments/                   # 後續模型回測與對照研究
├── tests/                         # 後續測試案例及驗證
└── research/                      # 領域研究及證據整理
```

## 技術規劃

| 系統層級 | 預計技術 |
| --- | --- |
| 網頁介面（Web UI） | React / Next.js |
| AI Agent／API 服務 | Python / FastAPI / LLM Function Calling（白名單工具） |
| 資料處理與儲存 | 環境部 API、CSV ETL、SQLite；必要時 PostgreSQL |
| 預測模型 | pandas、scikit-learn、XGBoost；SHAP 作可選解釋工具 |
| 領域知識與規則 | 經來源核實且有版本的官方 AQI 指引 |
| 測試與品質驗證 | pytest、時間序列前推回測、Agent 情境測試 |

技術棧屬**設計選型**，尚未安裝或部署；實際安裝及執行指令會在程式完成並驗證後補上；此階段不提供尚無法執行的指令。

## 官方資料來源

- 環境部 [AQX_P_432：空氣品質指標 AQI（每小時）](https://data.moenv.gov.tw/dataset/detail/AQX_P_432)
- 環境部 [AQX_P_488：空氣品質指標 AQI（歷史資料）](https://data.moenv.gov.tw/dataset/detail/AQX_P_488)
- 環境部 [AQX_P_13：空氣品質監測小時值](https://data.moenv.gov.tw/dataset/detail/AQX_P_13)
- 環境部 [AQI 與健康影響及活動建議](https://airtw.moenv.gov.tw/cht/Information/Standard/AirQualityIndicatorNew.aspx)

資料使用應遵守原始來源條款、頻率限制與署名要求；不在倉庫公開 API 金鑰、私人資料或未經授權再散布的資料。

## 研究與安全邊界

AirGuard AI **不是**官方空氣品質預報或個人醫療診斷服務。測站觀測不等於每一條街道的個人暴露量；模型不保證在每個測站或預測時距勝過簡單基線。資料過期、缺失、來源衝突或預測範圍不足時，系統必須揭露限制，不能捏造即時數值與健康保證。

本團隊專題目前為**提案階段**；實驗結果、正式部署與線上展示將在後續實作及驗證後提供。

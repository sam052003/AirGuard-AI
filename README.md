# AirGuard AI｜智慧空氣品質預測與生活決策代理人

**物聯網數據分析與應用（AIoT-DA）｜三人團體期末專題**

**第二組｜組長：林宏陽（7115056179）｜組員：蔡明憲（7115056013）、許鈵昆（8114056002）**  
**研究與設計修訂：2026-11-24｜版本：v3（依公開資料重新收斂可實作範圍）**

> **目前為 W1 資料工程完成、待進入 W2 Baseline 階段**：已完成環境部 `AQX_P_07`、`AQX_P_432`、`AQX_P_488`、`AQX_P_13` 真實 API 欄位核實、臺中市 6 座官方測站盤點、分頁原始快照保存（`--raw-dir`）與離線重算驗證、33 個月份逐時 PM2.5 品質報告，以及 19 項離線單元測試；ML 模型訓練、Agent、Web 與正式回測實驗尚未執行。原始與 v3 提案文件均保留於 `docs/proposal/`。

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

本組為**第二組**，組長林宏陽（7115056179），組員蔡明憲（7115056013）、許鈵昆（8114056002）。**目前不預先分工**。

## 7. 文件導覽與目前狀態

- [Deep Research｜五個思維模式、三項爭論及十個深度問題](research/deep-research-v3-evidence-2026-11-24.md) — 追加原始文獻、正反證據、共識、未解問題及本組驗證方案。

- [DESIGN.md](DESIGN.md) — 八模組、資料流、AI Agent、ML、API 與安全條件。
- [可實作性審查](docs/feasibility-audit.md) — 逐項判斷公開資料是否足以支援。
- [需求與驗收規格](docs/requirements.md) — FR-01～FR-12、P0／P1／排除範圍。
- [官方資料來源](docs/data-sources.md) — 欄位、授權碼、下載與可靠性風險。
- [實驗計畫](docs/evaluation-plan.md) 與 [開發路線圖](docs/implementation-roadmap.md)。
- [版本變更記錄](docs/decisions/2026-11-24-scope-decision.md) — 說明為何取消路線導航必做承諾。
- [myplan 文件索引](myplan/README.md) — 後續原始摘要與研究需求的重新整合。

**目前狀態**：W1 資料處理已完成 19 項離線單元測試，並於本機透過 `MOENV_API_KEY` 完成環境部 `AQX_P_07`（臺中 6 站座標）、`AQX_P_432`（即時 AQI）、`AQX_P_488`（歷史 AQI）與 `AQX_P_13`（2024-03-11～2026-11-23 逐時 PM2.5 原始分頁快照、SHA256 驗證與品質報告）本機實測；GitHub Actions CI 僅執行離線合成 fixture 測試；ML 模型、Agent 與 Web Demo 尚未開發。


## 8. W1 官方資料接入、環境變數設定與品質檢查（2026-11-24）

- **已寫程式與測試**：環境部 `AQX_P_07` 測站座標解析、`AQX_P_432` 與 `AQX_P_488` 的官方 AQI／當小時 PM2.5／移動平均 PM2.5 分離、`AQX_P_13` 的 24 小時寬表轉長表、分頁擷取與嚴格白名單 `filters` 驗證、原始分頁回應快照保存（`--raw-dir`）與離線重算（`--input <raw_dir>`）、同站同時刻重複紀錄策略（`error`／`dedup_identical`／`flag_conflict`）、每站×每月完整率（明確區分整月日曆達標與局部視窗達標）與 1／3／6h 有效樣本對數統計、`.env` 環境變數載入（系統環境變數未設定或為空字串時自動回退讀取 `.env`）與 Key 保護。
- **19 項離線測試已通過**；`data/fixtures/` 內均為**合成測試資料，不是官方監測結果**。
- **本機已完成真實 API 驗證與原始快照重算**：確認臺中市 6 座官方測站（豐原 `28`、沙鹿 `29`、大里 `30`、忠明 `31`、西屯 `32`、臺灣大道 `88`）與 2024-03-11～2026-11-23 逐時 PM2.5 品質統計（一般站涵蓋 33 個月：其中 31 個整月日曆完整率 ≥80%，首尾 `2024-03` 與 `2026-11` 為局部邊界月）。
- **未完成／待後續階段**：W2 Baseline 與 ML 模型訓練、Agent、Web 介面。不能將 W1 等同 P0 全部功能完成。
- 詳見 [W1 安裝、測試與真實資料驗證報告](docs/w1-data-integration.md)；Python 3.10+。

### Windows PowerShell 設定與執行步驟（優先使用 `py`）

1. 在專案根目錄將 `.env.example` 複製為 `.env`，並填入向環境部申請的 `MOENV_API_KEY`（`.env` 已被 `.gitignore` 排除，切勿提交至 GitHub；若系統已設定 `$env:MOENV_API_KEY`，程式會優先使用系統環境變數）：

```powershell
Copy-Item .env.example .env
# 編輯 .env 填入 MOENV_API_KEY=您的環境部金鑰
```

2. 安裝套件（套用 `requirements.lock.txt` 版本約束）並執行離線單元測試與合成資料驗證：

```powershell
py -m pip install -c requirements.lock.txt -e .
py -m unittest discover -s tests -v
py -m airguard --dataset AQX_P_13 --input data/fixtures/aqx_p_13_synthetic.json
```

3. 使用本機 `.env` 或 `$env:MOENV_API_KEY` 執行環境部官方 API 真實資料核對、保存原始各頁回應快照（`--raw-dir`，位於已被 Git ignore 的 `data/raw/`）並驗證離線快照重算：

```powershell
py -m airguard --dataset AQX_P_07 --live --county 臺中市 --raw-dir data/raw/aqx_p_07_taichung
py -m airguard --dataset AQX_P_432 --live --county 臺中市 --raw-dir data/raw/aqx_p_432_taichung
py -m airguard --dataset AQX_P_488 --live --station-id 32 --limit 100 --raw-dir data/raw/aqx_p_488_site32
py -m airguard --dataset AQX_P_13 --live --station-id 32 --limit 500 --max-pages 2 --on-duplicate dedup_identical --raw-dir data/raw/aqx_p_13_site32 --report-output data/normalized/aqx_p_13_site32_report.json

# 不需網路與 API Key，直接由本機原始回應快照驗證 SHA256 並重算一致的品質報告
py -m airguard --dataset AQX_P_13 --input data/raw/aqx_p_13_site32 --station-id 32 --on-duplicate dedup_identical
```


## 9. Antigravity × ChatGPT × GitHub 開發協作規範（2026-11-24）

**目前實際由一位專案負責人主導，Antigravity 負責程式實作，ChatGPT 負責 PR 技術審核**（第二組三人課程提案資料維持不變，不預設另外兩人參與開發）。流程：GitHub Issue → Antigravity 功能分支與測試 → Pull Request → ChatGPT 查看最新 Diff／CI 並留言 → Antigravity 修正（需要時）→ **專案負責人確認 CI 通過、無未解決 BLOCKER 後決定 Merge**。不需第二位真人核准；ChatGPT `COMMENTED` 不等於正式 GitHub `APPROVED`，亦不會自動巡檢或合併。

- [AGENTS.md](AGENTS.md)：提供 Antigravity 與 ChatGPT 的權責、P0／P1 邊界與不允許行為。
- [協作流程](docs/development-workflow.md)、[Reviewer 固定清單](docs/reviewer-checklist.md)。
- [API Contract](docs/api-contract.md)：`/api/v1` 規劃端點、請求／回覆、錯誤碼；**尚非已部署 API**。
- [真實資料驗證 Gate](docs/data-validation-protocol.md)、[依賴版本策略](docs/dependency-policy.md)。
- [Agent 30 情境驗收規格](docs/agent-test-plan.md)：目前僅為**尚未執行的測試規格**。
- [Antigravity W1 下一步 Prompt](docs/prompts/antigravity-w1-next.md)與[ChatGPT PR 審核 Prompt](docs/prompts/chatgpt-pr-review.md)。
- [GitHub Actions Python CI](.github/workflows/python-ci.yml)：只驗證離線合成資料／契約範例；真實官方 API 須在組員持有金鑰的本機另行驗證。

.github/PULL_REQUEST_TEMPLATE.md 為 PR 模板，`.github/ISSUE_TEMPLATE/` 為 Issue 模板；建議倉庫管理員為 `main` 啟用 PR、Python CI 與禁止 Force Push，**但不要設定強制其他 Reviewer Approve**。目前 GitHub Rulesets 並未自動啟用，文件和 CI 檔本身也不會變更倉庫保護設定。


## 10. 第二組定稿版 Word／PPT（Deep Research 補強）

- [第二組 v3 Proposal Document（Deep Research 補強）](docs/proposal/AirGuard_AI_Proposal_v3_第二組_DeepResearch_補強.docx)：包含第二組組員資訊、五個思維模式、三項專業爭論與十個深度理解問題。
- [第二組 v3 Proposal Presentation（Deep Research 補強）](docs/proposal/AirGuard_AI_Presentation_v3_第二組_DeepResearch_補強.pptx)：與報告相同的組員及研究架構。
- [Deep Research 文字版與研究證據](research/deep-research-v3-evidence-2026-11-24.md)。

以上為**2026-11-24 修訂文件**；原始提案與前次 v3 Word／PPT 均保留作版本追溯，不覆蓋或冒稱當時已包含修改。正式繳交平台若需要直接上傳檔案，仍須依課程規定另行提交。

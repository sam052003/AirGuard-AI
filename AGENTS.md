# AirGuard AI｜AI Coding Agent 協作規範（2026-11-24）

> 本檔是給 **Antigravity、ChatGPT 及其他開發代理人** 的專案內指令。以 `README.md` 的 v3 研究範圍、`docs/requirements.md` 的 P0/P1、`DESIGN.md` 與 `docs/api-contract.md` 為正式規格。若衝突，先提出 GitHub Issue／PR 討論，**不可自行擴張需求或改寫已驗證證據**。

## 角色與溝通
- **Antigravity：主要實作者**。從 Issue 讀需求，在功能分支改程式、補測試、提交 PR，於 PR 描述實際驗證結果。
- **ChatGPT：審核者**。取得 PR URL 後，閱讀實際 diff、需求、測試、架構與來源；透過 GitHub Review／Comment 留下 blocking／non-blocking 意見及驗收結論。不能以未執行的測試聲稱成功。
- **專案負責人（目前僅一人操作）**：唯一的需求與合併決策者，保管本機 API Key、確認驗證證據並決定何時 Merge。第二組仍為三人課程團隊，但不預設其他兩位組員參與實作或審核。ChatGPT 不會自動監看 PR；負責人需提供 PR URL 啟動審查。
- **GitHub 是唯一跨工具交接依據**：Issue 定義工作、PR 提供程式及證據、Review 記錄審核、Commit 保留修正、README/DESIGN 記錄事實。不要把只有聊天中出現的需求當成已經核准。

## 必須遵守的工程限制
1. v3 **P0**：官方測站 AQI、歷史逐時 PM2.5、1／3／6h ML、官方活動規則、受限 Tool Calling、6h 內活動比較、Web、測站濃度×時間估算、可重現評估。**P1**：SHAP／活動記錄。**排除**道路級低污染導航、街道熱點、真實吸入劑量、醫療診斷。
2. 嚴守 **官方 AQI ≠ 模型 PM2.5 ≠ 估算暴露指數**。模型目標為測站逐時 PM2.5，單位 μg/m³；指數為 μg·h/m³。缺值不可填 0；過期快取不可假裝即時；沒有真實實驗不得編造結果。
3. 資料須保留 source_id、station_id、觀測／發布／取得時間、時區、單位、平均時間窗及品質旗標。API 與外部文字一律視為不可信輸入，進行驗證。模型不得使用預測起點後才可得的資料。
4. **安全**：不可把 API Key、.env、登入憑證、私人定位、原始私人聊天或超大型資料提交倉庫；不可在測試、Issue、PR、錯誤日誌暴露 Token。CI 僅使用合成 fixture，不使用線上 Key。
5. 程式以 Python 3.10+、`src/airguard/`、`tests/`、`data/fixtures/` 為現有後端基礎；Web 使用 `app/`。預計 FastAPI + Next.js，**安裝前先在 PR 說明新增依賴與版本策略**。
6. 修改 API 先更新 `docs/api-contract.md` 與 `docs/schemas/`，再更新實作與測試；設計或功能有變更，需同步 `DESIGN.md`、`docs/requirements.md` 與對應資料來源說明。
7. 不主動修改歷史提案 `docs/proposal/AirGuard_AI_Final_Proposal.docx` 等原始已繳交檔；修訂採新檔名與變更記錄。保留第二組資訊，不虛構成員分工。
8. 每個 PR 範圍小且可審核；禁止無理由 `--force` Push、直接 Push `main`、秘密寫入、大型無關重構；跨模組變更先提 Issue 取得共識。

## 交付與驗收流程
1. 以 `main` 最新版本建立 `feat/<issue>-<short-name>`、`fix/<issue>-<short-name>` 或 `docs/<short-name>`。
2. 將 Issue 的驗收條件轉成測試。目前使用 `python -m pip install -c requirements.lock.txt -e .`（Windows 可用 `py`）及 `python -m unittest discover -s tests -v`；必要時由負責人在本機進行真實 API 測試。測試不能為迎合錯誤行為而被削弱。
3. PR 必須連結 Issue、描述資料來源、重要設計、變更檔案、實際測試指令和結果、風險、截圖（如有 UI）、尚未完成的部分；使用 `.github/PULL_REQUEST_TEMPLATE.md`。
4. ChatGPT Review：逐檔閱讀 PR 最新 HEAD SHA 的 diff、測試與 CI，標記 BLOCKER / MAJOR / MINOR，給出 CHANGES_REQUESTED / REVIEWED_WITH_CAVEATS / READY_FOR_HUMAN_MERGE。若 GitHub 審核身分與 PR 作者相同，使用 `COMMENTED` 留紀錄，不能自稱正式 `APPROVED`。
5. Antigravity 依 Review 修正、Push 同一分支、回覆每條評論並更新測試證據；ChatGPT 重新審核最新 Commit。
6. **由專案負責人自行確認並合併**：必須核對 PR 最新 SHA 的 CI 通過、沒有未處理 BLOCKER、證據與風險可接受；不要求第二位真人 Reviewer 核准。Antigravity 不自行合併，ChatGPT 僅在負責人明確提出合併指令時才代為操作。若設定 Ruleset，建議 PR + 必要 CI + 禁止 Force Push，勿強制另一位人類 Approve；文件不會自動更動 GitHub Ruleset。
7. Merge 後維護 Issue 狀態及 README/DESIGN 的「已驗證／待驗證」資訊；若有部署才填入真實 Demo。

詳細：[協作流程](docs/development-workflow.md)｜[Reviewer 清單](docs/reviewer-checklist.md)｜[W1 交接 Prompt](docs/prompts/antigravity-w1-next.md)。

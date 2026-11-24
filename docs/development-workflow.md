# 第二組｜Antigravity × ChatGPT × GitHub 協作流程

**正式分工模式（工具）**：Antigravity 實作、ChatGPT 審核、GitHub 儲存需求與交接。三位組員未預先指定各工作模組；組員自行安排 Issue 與最終合併決策。

## 唯一交接流程

```mermaid
flowchart LR
  I["GitHub Issue：需求＋驗收"] --> A["Antigravity：功能分支＋程式＋測試"]
  A --> P["GitHub PR：差異＋證據＋限制"]
  P --> R["ChatGPT：讀 diff／Review／阻擋項"]
  R --> D{"需要修改？"}
  D -- 是 --> A
  D -- 否 --> H["組員檢查 CI＋Review"]
  H --> M["GitHub 合併 main"]
  M --> I2["更新 Issue／README／DESIGN"]
```

### 實作端：Antigravity
1. `git fetch origin && git switch main && git pull --ff-only origin main`
2. 在 GitHub Issue 寫明：問題、範圍、相關 FR、資料來源、失敗狀態、驗收條件、測試。沒有 Issue 先建立，不自行擴張到 P1 或路線功能。
3. `git switch -c feat/<issue>-<slug>`；讀 `AGENTS.md`、`DESIGN.md`、SRS、API Contract、相依測試。
4. 最小變更、增加離線測試、文件同步，`git add`、`git commit`、`git push -u origin <branch>`，建立 PR（可以 Draft）。
5. 使用 PR Template 填寫完整內容；**禁止在 PR 填假測試結果**。

### 審核端：ChatGPT
- 使用者在 ChatGPT 傳「請審核 `https://github.com/sam052003/AirGuard-AI/pull/N`，以 main 的 AGENTS／SRS／DESIGN／API Contract 為準」。
- ChatGPT 必須取得最新 PR changed files 與 diff，必要時讀完整檔、CI 狀態、Issue 和相關測試；不能只憑 Antigravity 描述核准。
- 在 GitHub PR 建立 Review 或 Comment，列出 Blocking、重大及非阻擋項。若未能真正跑測試，註明「僅靜態審查」。
- 修正後使用者再次傳同一個 PR URL 請重新審核**最新 SHA**。ChatGPT 不會在沒有新對話指令時自動巡檢或合併。

### 人工作業與權限
- **合併前**：CI 完成且通過、無未處理 Blocker、需求符合、實測記錄誠實、至少一位非作者組員 Review（如可行）。
- **GitHub Rulesets**：由倉庫管理員在 Settings → Rules → Rulesets 設定 `main` 必須經 PR、必要狀態檢查、禁止 Force Push；若提供的帳號或方案不支援，至少採團隊協議。只是新增 YAML 不會自動替 `main` 設定分支保護。
- 若 ChatGPT 以**同一 GitHub 使用者帳號**寫 Review，GitHub 不允許同帳號替自己的 PR 進行正式核准；此時採 COMMENT，改由其他組員作正式審核。
- API Key 僅存本機或部署 Secrets。外部真實資料需由能合法存取的組員執行；CI 不要求金鑰。

## 必要命名及交接格式

Issue 標題：`[W1][FR-02] 臺中測站資料盤點與缺值報告`

Branch：`feat/12-station-quality-report`

PR 標題：`feat(data): 加入逐時資料品質報告 (#12)`

PR 內：`Closes #12`、變更摘要、實測命令及輸出、風險與回退、設計修改、未驗證項目。

Review 內：`Verdict: CHANGES_REQUESTED / REVIEWED_WITH_CAVEATS`，每項為 `[BLOCKER|MAJOR|MINOR] 路徑：原因→驗證→修正`。

## 最後期末交付物
在真正完成後才新增真實的安裝／執行、資料、模型版本、指標、Demo、Final PPT（超過 20 頁）、YouTube 影片（超過 10 分鐘）、限制與結論；不得因 PR 文件寫了預期結果就宣稱已實測。

[AGENTS.md](../AGENTS.md)｜[PR 審核清單](reviewer-checklist.md)｜[開發路線](implementation-roadmap.md)

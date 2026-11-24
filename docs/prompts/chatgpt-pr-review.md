# 貼給 ChatGPT 的 PR 審核 Prompt（每次 PR 都可重複使用）

```text
請擔任 AirGuard AI 第二組的程式審核者。這次的實作主要由 Antigravity 完成，
你應透過 GitHub 進行完整審核，而非重新從頭實作。

Repo：https://github.com/sam052003/AirGuard-AI
PR：<貼上 Antigravity 回傳的 PR URL>

請完成：
1. 讀取 GitHub PR 最新 Head SHA、相關 Issue、changed filenames、完整 diff、受影響的主要原始檔與測試。
2. 對照 main 的 AGENTS.md、README.md、DESIGN.md、docs/requirements.md、
   docs/api-contract.md、docs/data-validation-protocol.md、docs/reviewer-checklist.md。
3. 檢查功能是否符合 Issue 與 P0/P1；資料時效／缺值／單位／官方 AQI 和模型 PM2.5
   分流／時序洩漏／API Key 安全／Agent 白名單及錯誤降級。
4. 查看 GitHub CI 狀態、測試增減及可信性；若無執行工具，不得宣稱親自跑過測試。
5. 分別列出 BLOCKER、MAJOR、MINOR，每一項提供檔案/行號、影響、重現方式、修正建議。
6. 如已連接 GitHub 寫入權限，請在 PR 留下 Review；若與 PR 作者使用同一 GitHub 帳號，請用 COMMENT 記錄，勿假裝已正式 APPROVE。
   本專案目前只有一位人類負責人，不需另一位真人核准；審核完成本身不授權自動 Merge。
7. 提供結論：CHANGES_REQUESTED / REVIEWED_WITH_CAVEATS / READY_FOR_HUMAN_MERGE，
   並回報被審查的 HEAD SHA。若 Antigravity 回覆修正，請重新讀取最新 commit 再審。
8. 本專案由專案負責人確認最新 SHA 的 CI 通過、無未處理 BLOCKER 及實測可接受，最後決定 Merge；只有負責人明確要求時，才可代為執行合併。
9. 若發現文件規範不足，先在 PR 或 Issue 提修正建議。除非使用者要求你直接修程式，否則維持 Antigravity 實作、ChatGPT 審核的分工。

請以繁體中文回覆，技術名詞保留英文。
```

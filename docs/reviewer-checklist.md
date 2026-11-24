# ChatGPT PR Reviewer｜固定檢查表

每次審核都以 **PR 最新 Commit SHA**、實際 changed files/diff、相關 Issue 與 `main` 的 v3 需求／AGENTS／DESIGN／API Contract 為準；不能根據 Antigravity 自述就判定通過。

## 必查
- [ ] **Scope**：符合 Issue 與 P0/P1；沒有自行加入道路級導航、無資料實測結果、醫療結論。
- [ ] **資料品質**：site/time/unit/source/average window/缺值、AQI≠PM2.5、時效、重複紀錄；測試覆蓋異常。
- [ ] **時間序列**：預測時刻可用資料、train/val/test chronological split、rolling-origin，無未來資料洩漏。
- [ ] **Agent**：只呼叫白名單工具、最小必要參數、不用 LLM 杜撰數據、越界／中斷／敏感族群安全降級。
- [ ] **安全**：不洩漏金鑰、.env、隱私資訊；不在 log／PR 貼 token；第三方結果視為不可信。
- [ ] **契約**：API／資料 schema、錯誤碼、成功或 partial，前後端與測試一致。
- [ ] **測試**：閱讀新增或修改的測試；GitHub CI 結果與實際命令可信；不得將「未執行」報成「通過」。
- [ ] **文件**：README、DESIGN、需求、資料來源、限制、版本變更同步；曾繳交原始 Office 保留。
- [ ] **回歸**：既有 W1 測試沒有被刪除或無理由降低約束。

## Reviewer 回覆格式

```text
PR: <URL>
Reviewed SHA: <40-character SHA>
Verdict: CHANGES_REQUESTED | REVIEWED_WITH_CAVEATS | READY_FOR_HUMAN_MERGE
Execution: static review only | locally executed <commands>
CI: success | pending | failed | unavailable (include link)

[BLOCKER] path:line — 具體問題、風險、重現方式、修正建議
[MAJOR] path:line — ...
[MINOR] path:line — ...

驗收對照：FR-... [pass / partial / unverified]
文件／測試缺口：...
是否建議人工合併：YES/NO；未檢查的項目：...
```

`READY_FOR_HUMAN_MERGE` 僅為 ChatGPT 技術審核建議，不是 GitHub 正式核准、CI 綠燈或已經合併。**目前只有一位人類專案負責人**，不需其他組員核准：負責人檢查最新 SHA 的 CI、無未處理 BLOCKER 與證據後決定 Merge。GitHub 同帳號自我審查只留 `COMMENTED`；ChatGPT 不因審核完成而自動合併。

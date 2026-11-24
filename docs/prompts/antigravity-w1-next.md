# 貼給 Antigravity 的第一個正式實作 Prompt：W1 真實資料盤點

> 工作依據：`AGENTS.md`、`docs/development-workflow.md`、`docs/requirements.md`、`docs/data-validation-protocol.md`、`docs/api-contract.md`。此文件同時供 ChatGPT 審核時核對交辦條件。

```text
你現在是 AirGuard AI（第二組）的主要程式實作者 Antigravity。
正式 GitHub：https://github.com/sam052003/AirGuard-AI
技術審核由 ChatGPT 在 GitHub Pull Request 完成；請不要直接 Push main。

第一步：clone / git pull，讀取 AGENTS.md、README.md、DESIGN.md、docs/requirements.md、
docs/w1-data-integration.md、docs/data-validation-protocol.md、docs/api-contract.md、
CONTRIBUTING.md 和所有現有 tests，先簡要回報現況。
先到 GitHub 找對應的 W1 Issue，沒有就建立，並在分支 feat/<issue>-data-quality 實作。

本次只做 W1 / FR-01 / FR-02 的「官方資料可靠性與品質盤點」：
1. 擴充 AQX_P_13 逐時資料的可重現分頁／批次輸入處理、錯誤回報與資料來源追蹤。
2. 新增 AQX_P_07 官方測站基本資料解析，串出臺中候選站清單；座標系統與欄位格式需依官方回應驗證。
3. 輸出每站 × 月份的預期時槽、有效時數、缺值／異常數、coverage 與時間窗；保留測站／資料來源／sha256。
4. 所有真實呼叫都需 MOENV_API_KEY，使用者自行本機設定；不要索取、輸出、提交任何 API Key。
5. 若沒有可用金鑰，請使用標記為 synthetic 的測試 fixture 實作與測試，將「真實 API 尚未驗證」列為 PR 未完成，不要假造臺中監測值。
6. 時區一律清楚區分 Asia/Taipei、UTC；published_at 不能以 fetched_at 代替；缺值不能用 0；AQI 不等於 PM2.5。
7. 遵守既有 src/airguard/、tests/ 佈局，不要開始 ML、Agent、Web，也不要改動 docs/proposal/ 原始已繳交檔。
8. 對正常、缺值、錯誤單位、重複、分頁邊界、schema 變更與時區增加單元測試；保留現有 8 題。
9. 執行 python -m pip install -e .；python -m unittest discover -s tests -v，
   將真實結果貼入 PR；不要未跑先寫全部通過。
10. 如資料契約變更，更新 docs/api-contract.md、docs/schemas/、DESIGN.md；
    如增加依賴，遵守 docs/dependency-policy.md。
11. Commit 到功能分支，開 GitHub PR 至 main，PR 內容符合 .github/PULL_REQUEST_TEMPLATE.md，
    附上 changed files、測試輸出、資料範圍與限制、回退策略。
12. 完成時只回報 PR URL 和目前 HEAD SHA，等 ChatGPT 在該 PR Review；
    若收到 BLOCKER，修正同一 PR 並回覆評論。不得自行合併 main。

驗收 Gate：至少一個可由官方來源確認的臺中測站；可重算的資料品質報告；
合成資料可完整離線測試；真實 API 沒有金鑰時明確標示尚未驗證。
```

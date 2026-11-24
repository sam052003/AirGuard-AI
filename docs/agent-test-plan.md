# Track B｜Agent 固定 30 情境驗收規格（設計中）

這份測試集依 `docs/evaluation-plan.md` 的 **6 類 × 5 例** 規劃，機器可讀資料為 [agent-acceptance-cases.json](agent-acceptance-cases.json)。**所有 execution_status = not_run**：目前 Agent 尚未實作，這 30 題只是預期行為規格，不是假測試結果。

## 案例分類
| 類別 | 前綴 | 內容 |
|---|---|---|
| 正常活動 | A01–A05 | 時段、時長、不確定性及超時距 |
| 敏感族群 | B01–B05 | 官方指引、保守表述與非醫療診斷 |
| 地點／時間歧義 | C01–C05 | 測站辨識、必要澄清 |
| 失效與品質 | D01–D05 | API 故障、缺值、來源與單位 |
| 預測時距 | E01–E05 | 1／3／6h 邊界與越界 |
| 來源與安全 | F01–F05 | 不杜撰數值、引用、道路級限制及 Prompt Injection |

## 真正執行後的計分
- 每個案例要有固定 `given`（合成工具回應／可用模型狀態）、`when`（查詢）、`then`（必須行為、禁止行為），測試前凍結資料版本。
- `tool_selection_accuracy`：選對工具且參數正確的比例；`source_completeness`：必要來源、時間與單位齊全比例；`rule_consistency`：符合相同版次官方指引比例；`safe_fallback_rate`：可重現失效案例合格比例。
- 各指標分母只取適用案例，記錄跳過／不適用／錯誤，另報 median/P95，並比較 Rule-only 與 Agent+ML+Rules。
- **CI 目前只檢查本規格的 JSON 格式與 30 題完整性**，不會宣稱實際 Agent 已通過。上線前需新增真正的 Agent 整合測試，更新每題執行記錄與證據。

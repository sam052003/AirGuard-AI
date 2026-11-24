# PR｜摘要
Closes #<!-- GitHub Issue 編號，無則先建立 -->

## 目的與需求
- 目標：<!-- 一句說明 -->
- 對應 FR：<!-- 如 FR-02 -->
- 範圍：<!-- P0 / P1；是否超出本次 Issue -->

## 實際變更
- 程式／文件：
- API、資料欄位、模型或 Domain Rules 變更（如有）：

## 實際驗證（只填執行過的）
- [ ] `python -m pip install -e .`
- [ ] `python -m unittest discover -s tests -v`
- [ ] 本次更動專用測試：
- [ ] CI 已通過（若尚未跑完寫「pending」）
- **輸出摘要、環境、Python 版本、測試證據**：
- **資料模式**：synthetic fixture / live MOENV / historical snapshot / not run
- **真實資料來源、站點、期間與 SHA256**（未使用填 N/A）：

## 安全、失效與可重現性
- [ ] 沒有把 `.env`、API Key、私人資料或大型原始資料提交
- [ ] 官方 AQI／PM2.5 模型預測／估算暴露明確分開
- [ ] 缺值、過期、時距、單位和站點尺度有對應處理／測試
- [ ] 依賴與 lockfile（若新增第三方套件）已更新
- [ ] README／DESIGN／API Contract／SRS（如適用）已同步

## 風險與未完成
- 可能的回歸風險及回退：
- 沒有驗證、需要 API Key、待辦事項：
- 畫面截圖／影片（若 UI 更動）：

## ChatGPT Reviewer 交接
- **PR 最新 HEAD SHA**：
- **請審核**：實際 diff、相依測試、SRS、AGENTS.md、API 契約與安全邊界
- **審核狀態**：waiting / changes requested / rereview requested / reviewed
- **合併**：必須由組員確認 CI、未處理 Blocker 與實際審核後操作；AI 自述「通過」不構成 GitHub Review 批准

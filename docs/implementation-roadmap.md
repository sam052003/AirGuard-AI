# AirGuard AI｜六階段實作路線（P0 優先）

| 階段 | 任務 | 完成證據 |
|---|---|---|
| W1 | 環境部 Key／下載、測站與月份資料盤點、來源與 Schema | API／CSV 樣本、站點資料字典、缺值／時間報告 |
| W2 | PM2.5 時序 Baseline、資料切分與初步前向回測 | Persistence、Seasonal Naive 的有效 MAE／RMSE |
| W3 | Ridge／Random Forest／XGBoost 與誤差檢視 | 不洩漏的可重現 ML 比較及模型版本 |
| W4 | Agent 白名單工具、官方 AQI 規則與資料安全降級 | Agent Tool Trace、30 題測試草案、單元測試 |
| W5 | Next.js／FastAPI、測站地圖、活動比較、濃度×時間估算 | Web 可操作原型、來源卡與失效畫面 |
| W6 | 固定測試、失敗案例、文件與最終展示 | 模型／Agent 指標、README、DESIGN、Demo 與限制 |

**P1 延伸**：在 W1～W6 P0 交付後，視開發進度加入 SHAP 與手動每日活動紀錄（不影響核心驗收）。上述週數為**開發建議**，不表示老師已給予 6 週期限。

## 里程碑 Gate

- G1：有可下載、可重算的臺中逐時 PM2.5 資料與清楚缺值處理。
- G2：Baseline + ML + temporal split；模型未勝 Baseline 仍如實報告。
- G3：Agent 和固定領域規則可用固定案例重播。
- G4：活動結果能呈現資料時間、來源、單位、估算與失效限制。
- G5：Web Demo、測試數據與 GitHub 文件內容一致。

**不再設 M3 道路級導航 Gate**：目前無充分的公開道路污染資料與獨立驗證，不把做不到的功能當成必要交付。

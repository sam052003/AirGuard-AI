# AirGuard AI v3｜更新方式（不覆蓋舊提案）

這份 ZIP 是對**既有** `https://github.com/sam052003/AirGuard-AI` 的**覆蓋式更新包**，不是全新可執行程式。解壓縮後應與本機 Git Repository 合併，**不要刪除原有 `.git`、原始 DOCX／PPTX 或其他檔案**。

## 1. 建議先建立備份分支

```bash
git switch main
git pull --ff-only origin main
git switch -c docs/feasible-scope-v3
```

## 2. 解壓縮、複製內容

將 ZIP 裡的 `README.md`、`DESIGN.md`、`docs/`、`myplan/`、`UPDATE_INSTRUCTIONS.md` **依相同路徑**複製到本機 `AirGuard-AI/` 根目錄；提示覆蓋 markdown 文件時選擇覆蓋。原本 `docs/proposal/AirGuard_AI_Final_Proposal.docx` 及 `AirGuard_AI_Final_Proposal_Presentation.pptx` 應保留且不要覆蓋。

新增修訂版：

- `docs/proposal/AirGuard_AI_Proposal_Feasible_v3.docx`
- `docs/proposal/AirGuard_AI_Proposal_Presentation_Feasible_v3.pptx`

修改團隊姓名／學號時只填寫實際資料，不要推測，也不要在 GitHub 公開不必要的個資。

## 3. 本機檢查、Commit

```bash
git status
git diff --stat
git add README.md DESIGN.md docs myplan UPDATE_INSTRUCTIONS.md
git commit -m "docs: 收斂 AirGuard AI 可實作功能與公開資料依據"
git push -u origin docs/feasible-scope-v3
```

回到 GitHub，開 Pull Request（base `main`, compare `docs/feasible-scope-v3`），確認新舊版本後 Merge，讓原始提交在 Git 歷史中保留。

如果只想直接 Push main，可在 `main` 執行同一組 add／commit，再 `git push origin main`；但文件大幅調整時，**建議用 Pull Request**。

## 4. 完成後檢查

- README／DESIGN／SRS：路線級污染排行不再標成必做。
- 原始 Word／PPT 仍在原路徑，新增 v3 修訂版。
- v3 Word／PPT 一致為 1／3／6h ML、官方資料、受限 Agent、活動比較、站點濃度×時間、Track A／B；SHAP 是 P1。
- 所有功能「規劃／待實測」與實際專案狀態相符。
- 官方 API Key 不應上傳至 GitHub。

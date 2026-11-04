# 發布至 GitHub

本文件說明本組如何將已整理完成的 AirGuard AI 團體專題檔案建立為正式 GitHub 儲存庫。`AirGuard-AI` 為建議倉庫名稱。

## 建立新倉庫

1. 由團隊協議選擇 GitHub 帳號或 GitHub Organization 作為倉庫擁有者；進入 <https://github.com/new>。
2. 儲存庫名稱（Repository name）輸入 `AirGuard-AI`；簡介（Description）建議填入：`智慧空氣品質預測與生活決策 AI Agent｜整合環境部開放資料、PM2.5 短期預測與 AQI 活動指引`。
3. 可見性（Visibility）可選 Public（公開）或 Private（私人），依團隊及教師瀏覽需求決定。若選 Private，必須確保教師或助教有權存取。
4. **不要勾選** GitHub 自動建立的 README、`.gitignore` 或 License（授權條款），避免與此套件已有檔案產生第一次提交衝突。
5. 建立後，將壓縮檔解開，開啟終端機至 `AirGuard-AI` 資料夾，再執行以下命令。

```bash
git init -b main
git add .
git commit -m "docs: 建立 AirGuard AI 期末專題提案儲存庫"
git remote add origin https://github.com/OWNER/AirGuard-AI.git
git push -u origin main
```

將 `OWNER` 換成實際建立倉庫的個人帳號或組織名稱（由團隊決定），以新倉庫頁面顯示的網址為準。若 GitHub 要求驗證，使用 Git Credential Manager／瀏覽器授權等合法方式，不將 token 放在程式或 README 中。

## 團隊成員存取與協作設定

建立倉庫後，由擁有者依 GitHub 的 Repository Settings 邀請其他組員參與（Collaborators，或 Organization Team），依需要指派適當權限。建議使用各自帳號 Commit／開 PR，保留協作紀錄；不要共用密碼或 Access Token。正式繳交前確認所有組員與授課教師／助教具備所需閱讀權限。

詳細分支與 Pull Request 規則見 [`CONTRIBUTING.md`](../CONTRIBUTING.md)。

## 發布後確認

- 倉庫首頁可以看到 `README.md`、`DESIGN.md` 與 `CONTRIBUTING.md`。
- `docs/proposal/` 有正式 DOCX／PPTX 兩份檔案。
- `docs/architecture.mmd` 與 `docs/agent-flowchart.mmd` 可在 GitHub 開啟。
- 頁面顯示至少一筆初始提交紀錄（initial commit），預設分支為 `main`。
- `data/` 不含未授權大型資料，根目錄不含 `.env`、API Key 或模型檔。
- 已將其他組員加入倉庫／組織，GitHub 設定／教師存取權限符合課程繳交要求。

GitHub 儲存庫存在且可供老師瀏覽，才代表第三項提案交付完成；本機 ZIP 只是上傳準備檔，並非已發布的 GitHub 網址。

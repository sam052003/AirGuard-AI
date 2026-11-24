# Python／前端依賴版本與可重現性規範

目前 W1 `pyproject.toml` 僅包含一項輕量級執行期相依套件 **`python-dotenv>=1.0.0,<2.0.0`**（BSD-3-Clause 授權、無任何間接子依賴），用於在本機開發與 CLI 執行時載入 `.env`（優先保留非空之既有系統環境變數）；其餘資料解析、HTTP 與測試均使用 Python 標準函式庫。鎖定版本記錄於根目錄單一 pip constraints 鎖檔 `requirements.lock.txt`（`python-dotenv==1.2.4`），本機安裝與 GitHub Actions CI 皆統一執行 `python -m pip install -c requirements.lock.txt -e .`。

1. **Python**：遵循 `requires-python >=3.10`；CI 先以 Python 3.11、3.12 執行 unit tests。開發者應在 PR 說明本機版本。
2. **新增 Python 依賴**：先列用途、授權、安全與版本需求；在 `pyproject.toml` 明確聲明版本範圍。第一次新增外部套件時必須一併提交可重現的 lockfile／constraints（例如 `uv.lock` 或經鎖定的 `requirements*.txt`），決定單一工具並更新 CI 指令；**不要同時混用多份來源不一致的 lockfile**。
3. **Next.js**：建立 `app/` 時依選定套件管理器保留唯一 lockfile（例如 `package-lock.json`），CI 使用 `npm ci`、`npm test`／`npm run build`，不要僅 `npm install` 後不提交鎖檔。
4. **模型**：紀錄 Python／ML 套件版本、訓練程式 Git SHA、資料雜湊、random seed、特徵列表、切分與模型檔版本。
5. 不在 CI 安裝未使用的大型套件，不在 PR 寫「已鎖定」但沒有提交或測試實際鎖檔；依賴變更需至少一名非作者檢視。

目前 CI 與本機指引均使用 `python -m pip install -c requirements.lock.txt -e .`（Windows PowerShell 為 `py -m pip install -c requirements.lock.txt -e .`）套用鎖定版本。

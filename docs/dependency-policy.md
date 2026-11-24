# Python／前端依賴版本與可重現性規範

目前 W1 `pyproject.toml` 的 **runtime dependencies 為空**，解析、HTTP 與測試使用 Python 標準函式庫；因此不必為不存在的 pandas 或 LLM SDK 虛構 lockfile。這不代表未來整套系統不需要相依套件。

1. **Python**：遵循 `requires-python >=3.10`；CI 先以 Python 3.11、3.12 執行 unit tests。開發者應在 PR 說明本機版本。
2. **新增 Python 依賴**：先列用途、授權、安全與版本需求；在 `pyproject.toml` 明確聲明版本範圍。第一次新增外部套件時必須一併提交可重現的 lockfile／constraints（例如 `uv.lock` 或經鎖定的 `requirements*.txt`），決定單一工具並更新 CI 指令；**不要同時混用多份來源不一致的 lockfile**。
3. **Next.js**：建立 `app/` 時依選定套件管理器保留唯一 lockfile（例如 `package-lock.json`），CI 使用 `npm ci`、`npm test`／`npm run build`，不要僅 `npm install` 後不提交鎖檔。
4. **模型**：紀錄 Python／ML 套件版本、訓練程式 Git SHA、資料雜湊、random seed、特徵列表、切分與模型檔版本。
5. 不在 CI 安裝未使用的大型套件，不在 PR 寫「已鎖定」但沒有提交或測試實際鎖檔；依賴變更需至少一名非作者檢視。

目前 CI 用 `python -m pip install -e .` 安裝本專案；此舉**尚非完整 lockfile 等級的重現性**，在首次新增第三方 runtime dependency 前必須升級。

# 資料與樣本

`fixtures/` 的四份 JSON（`aqx_p_07_synthetic.json`、`aqx_p_13_synthetic.json`、`aqx_p_432_synthetic.json`、`aqx_p_488_synthetic.json`）均為**合成資料**，僅供離線單元測試，代碼 991、992、993、999 不是官方測站。真實資料應依法從環境部取得，並將原始及正規化檔案存於 Git 忽略的 `data/raw/`、`data/normalized/`；勿提交 `.env`、API Key、私人定位或未授權資料。詳見 [W1 指引](../docs/w1-data-integration.md)。

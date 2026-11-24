# 測試

`tests/test_moenv.py`（15 項）與 `tests/test_contracts.py`（4 項）共 19 項離線單元測試，覆蓋 `.env` 載入、空系統環境變數回退與系統環境變數優先序、`station_id`／`item_eng_name`／`filters` 嚴格白名單驗證、`AQX_P_07` 臺中站點與 TWD97 座標驗證、官方 AQI／當小時 PM2.5／移動平均 PM2.5 分離、逐時長表、缺值／無效值／可配置極端異常值門檻、重複時間處理策略（含 `flag_conflict` 原始值保留）、`--raw-dir` 分頁原始快照儲存與離線 SHA256 驗證重算、每站×每月品質報告（區分整月達標與局部視窗達標）與 1／3／6h 有效樣本對數、資料契約與金鑰保護。執行：`py -m unittest discover -s tests -v`。這些離線測試僅使用合成資料與假金鑰，不讀取本機真實 `.env`。

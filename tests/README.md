# 測試

`tests/test_moenv.py`（14 項）與 `tests/test_contracts.py`（4 項）共 18 項離線單元測試，覆蓋 `.env` 載入與系統環境變數優先序、`AQX_P_07` 臺中站點與 TWD97 座標驗證、官方 AQI／當小時 PM2.5／移動平均 PM2.5 分離、逐時長表、缺值／無效值／極端異常值、重複時間處理策略、分頁 SHA256 來源追蹤、每站×每月品質報告與 1／3／6h 有效樣本對數、資料契約與金鑰保護。執行：`py -m unittest discover -s tests -v`。這些離線測試僅使用合成資料與假金鑰，不讀取本機真實 `.env`。

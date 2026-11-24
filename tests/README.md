# 測試

`tests/test_moenv.py` 有 8 項 W1 離線測試，覆蓋官方 AQI／PM2.5 分離、逐時長表、缺值／無效值、重複時間、資料契約與金鑰保護。執行：`python -m unittest discover -s tests -v`。這些**不是**真實 API 串接測試或模型準確率測試。

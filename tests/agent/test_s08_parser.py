"""第五輪 S08 回歸測試：數量（公斤／小數／總價語意）、當次非法日期、月日補年規則與並發年隔離。

對應第四輪獨立審查 REVIEW_f146b97.md 的 S08（解析器只修示例，公斤、小數重量
與當次非法日期仍錯）。規則：先紅燈重現、修復後全綠；只改 tools.py 解析部分，
不動 service.py／providers.py／hermes_runner.py。
"""

from __future__ import annotations

import sys
import threading
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from aiot_price.agent.tools import parse_query

TODAY = date(2026, 10, 4)


class TestS08ReviewCases:
    """審查重現三案例（REVIEW_f146b97.md S08 表格）。"""

    def test_kg_quantity_total_price_converted(self):
        # S08-1：「2公斤80元」是總價 → 每公斤 40 元；不得直接當每公斤 80 元
        pq = parse_query("高麗菜今天2公斤80元", today=TODAY)
        if pq.current_price is not None:
            assert pq.current_price == 40, f"2公斤80元應換算每公斤40，實得 {pq.current_price}"
            assert pq.price_unit == "NTD_per_kg"
        else:
            assert pq.missing, "不換算時必須要求補充，不得猜"
        assert pq.current_price != 80

    def test_decimal_jin_quantity_not_misread(self):
        # S08-2：「0.5斤16元」→ 每斤 32 元；不得把 0.5 的尾數 5 當 5 斤算成 3.2
        pq = parse_query("高麗菜今天0.5斤16元", today=TODAY)
        if pq.current_price is not None:
            assert pq.current_price == 32, f"0.5斤16元應換算每斤32，實得 {pq.current_price}"
            assert pq.price_unit == "NTD_per_taiwan_jin"
        else:
            assert pq.missing
        assert pq.current_price != 3.2

    def test_current_invalid_date_requires_clarification(self):
        # S08-3：當次報價明示 2026-02-30（不存在的日期）→ 不得默默用今天＋32 元組請求。
        # 走 missing 機制要求澄清；服務層會再呼叫 to_forecast_request（內部重置
        # missing），因此提示必須能在其內部重現。
        pq = parse_query("高麗菜2026-02-30一斤32元", today=TODAY)
        req = pq.to_forecast_request()
        assert req is None, "當次非法日期不得以今天為觀測日組出預測請求"
        assert any("日期" in m for m in pq.missing), f"missing 須含日期無法解析提示，實得 {pq.missing}"


class TestS08NoRegression:
    """既有已修行為不得回歸（兩斤32、負價、混合單位、跨品項、上週非法日期、「上次」、月日 9/1）。"""

    def test_two_jin_total_still_converts(self):
        pq = parse_query("高麗菜今天兩斤32元", today=TODAY)
        if pq.current_price is not None:
            assert pq.current_price == 16, "兩斤總價要嘛換算單價16，要嘛要求確認；不得直接當32"
        else:
            assert pq.missing

    def test_negative_price_still_rejected(self):
        pq = parse_query("高麗菜今天一斤-32元", today=TODAY)
        assert pq.current_price != 32, "負號不得消失成 32"
        assert pq.missing or pq.current_price is None

    def test_mixed_units_still_bound_per_clause(self):
        pq = parse_query("高麗菜今天一斤32元，上週一公斤50元", today=TODAY)
        assert pq.current_price == 32 and pq.price_unit == "NTD_per_taiwan_jin"
        assert pq.previous_price == 50 and pq.previous_price_unit == "NTD_per_kg"

    def test_cross_crop_previous_still_rejects_b(self):
        pq = parse_query("高麗菜今天一斤32元，上週絲瓜一斤28元", today=TODAY)
        assert pq.b_reject_reason and "品項" in pq.b_reject_reason
        req = pq.to_forecast_request()
        assert req is None or req.get("mode") != "both"

    def test_previous_invalid_date_still_rejects_b(self):
        pq = parse_query("高麗菜今天一斤32元，上週2026-02-30一斤28元", today=TODAY)
        assert pq.previous_date != date(2026, 9, 27), "無效日期不等於未提供：不得補 t-7"
        assert pq.b_reject_reason or pq.previous_date is None

    def test_last_time_without_date_still_asks(self):
        pq = parse_query("高麗菜今天一斤32元，上次一斤28元", today=TODAY)
        assert pq.previous_price is None
        assert pq.b_reject_reason and "上次" in pq.b_reject_reason

    def test_month_day_still_parsed(self):
        pq = parse_query("高麗菜今天一斤32元，上週9/1一斤28元", today=TODAY)
        assert pq.previous_date == date(2026, 9, 1), f"9/1 應補今年解析成 2026-09-01，實得 {pq.previous_date}"


class TestS08QuantitySemantics:
    """數量綁定「總價語意」：僅數量在價格之前且同子句（兩斤32、2公斤80）才換算單價。"""

    def test_unit_price_with_trailing_purchase_clause(self):
        # 「每斤32元，共買兩斤」：單價已明示；後方子句只是購買數量描述，不得把 32 除以 2
        pq = parse_query("高麗菜每斤32元，共買兩斤", today=TODAY)
        assert pq.current_price == 32, "「每斤32」是單價；不得被後方「共買兩斤」換算成16"

    def test_unit_price_with_trailing_quantity_same_clause(self):
        # 同子句、數量在價格之後（任務重現形式）：「每斤32元共買兩斤」→ 32 是單價，
        # 後方的「共買兩斤」只是購買數量描述，不得把 32 除以 2
        pq = parse_query("高麗菜每斤32元共買兩斤", today=TODAY)
        assert pq.current_price == 32, "單價後綴數量描述不得觸發總價換算"

    def test_mei_marker_never_divides(self):
        # 「每」是單價基準詞，即使同子句出現數量也不換算
        pq = parse_query("高麗菜今天每斤32元", today=TODAY)
        assert pq.current_price == 32

    def test_kg_quantity_on_previous_clause(self):
        # 上週子句的總價換算：2公斤100元 → 每公斤 50
        pq = parse_query("絲瓜今天一公斤80元，上週2公斤100元", today=TODAY)
        assert pq.previous_price == 50, f"2公斤100元應換算每公斤50，實得 {pq.previous_price}"
        assert pq.previous_price_unit == "NTD_per_kg"

    def test_decimal_kg_quantity(self):
        # 1.5公斤90元 → 每公斤 60
        pq = parse_query("高麗菜今天1.5公斤90元", today=TODAY)
        if pq.current_price is not None:
            assert pq.current_price == 60, f"1.5公斤90元應換算每公斤60，實得 {pq.current_price}"
        else:
            assert pq.missing

    def test_fraction_jin_quantity(self):
        # 0.5 斤小數：16/0.5 = 32（總價換算對小數同樣成立）
        pq = parse_query("高麗菜今天0.5斤16元", today=TODAY)
        assert pq.current_price == 32


class TestS08MonthDayYearRule:
    """月日補年規則（保守版）：補今天年；若補出來的日期已在未來超過 30 天，視為無法解析
    （要求澄清），不回推上一年。規則記錄於 tools.py 註解。"""

    def test_month_day_far_future_flagged(self):
        # 12/25 補 2026 年 → 在今天（2026-10-04）未來 82 天（>30）→ 要求澄清
        pq = parse_query("高麗菜今天一斤32元，上週12/25一斤28元", today=TODAY)
        assert pq.previous_date != date(2026, 12, 25), "月日落在遠未來不得默默採用"
        assert pq.b_reject_reason or pq.previous_date is None

    def test_month_day_near_future_kept(self):
        # 10/20（未來 16 天，≤30）不誤擋：如實解析，合理性交由引擎端檢查
        pq = parse_query("高麗菜今天一斤32元，上週10/20一斤28元", today=TODAY)
        assert pq.previous_date == date(2026, 10, 20)


class TestS08YearIsolation:
    """月日補年不得依賴模組級全域（globals 覆寫）：並發請求的年份互不影響。"""

    _QUERY = "高麗菜今天一斤32元，上週9/1一斤28元"

    def test_sequential_different_years(self):
        pq25 = parse_query(self._QUERY, today=date(2025, 12, 31))
        assert pq25.previous_date == date(2025, 9, 1)
        pq26 = parse_query(self._QUERY, today=TODAY)
        assert pq26.previous_date == date(2026, 9, 1)

    def test_threaded_year_isolation(self):
        # 舊實作以 globals()["_DEFAULT_YEAR"] 傳年，兩個執行緒交錯時互相污染；
        # 修後每次解析的補年只由自己的 today 決定。
        errors: list[str] = []
        rounds = 200

        def worker(today: date, expect: date):
            for i in range(rounds):
                pq = parse_query(self._QUERY, today=today)
                if pq.previous_date != expect:
                    errors.append(f"today={today} 第{i}輪得 {pq.previous_date}，應為 {expect}")

        t1 = threading.Thread(target=worker, args=(date(2025, 12, 31), date(2025, 9, 1)))
        t2 = threading.Thread(target=worker, args=(TODAY, date(2026, 9, 1)))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert not errors, "; ".join(errors[:5])

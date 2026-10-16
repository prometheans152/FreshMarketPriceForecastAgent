# -*- coding: utf-8 -*-
"""Negative controls for the v5 deck generator table-geometry guard (REVIEW_R2 V4).

證明檢查器真的會抓錯：餵入 r2 實際發生過的壞欄寬（第3頁 4.00 吋、第4頁 2.95 吋）
與欄/列數不符的輸入，validate_table_geometry 必須 raise；正確幾何必須放行。
只測純函式，不生成簡報、不碰任何正式檔案。"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
import pytest

_SRC = Path(__file__).with_name('build.py')
_spec = importlib.util.spec_from_file_location('v5_build_guard', _SRC)
mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('v5_build_guard', mod)
_spec.loader.exec_module(mod)
validate = mod.validate_table_geometry

ROWS3 = [['A', 'B', 'C'], ['1', '2', '3'], ['4', '5', '6']]
ROWS4 = [['前作', '已知做法', '預測對象', '對照'], ['a', 'b', 'c', 'd'], ['e', 'f', 'g', 'h']]


def test_valid_geometry_passes():
    validate(ROWS3, [2.95, 3.55, 3.23, 2.20][:3], [.4, 1.0, 1.0], 9.73)  # sum==width


def test_sum_within_tolerance_passes():
    validate(ROWS3, [3.0, 3.0, 3.0], [.4, 1.0, 1.0], 9.0 + 0.05)  # tol=0.06


def test_r2_p3_bug_colwidths_must_fail():
    # r2 第3頁實際值：width=11.93、4欄 [.60,1.10,1.30,1.00]，欄寬總和=4.00（REVIEW_R2 V1）
    with pytest.raises(ValueError, match='colwidths sum'):
        validate(ROWS4, [.60, 1.10, 1.30, 1.00], [.40, 1.02, 1.02], 11.93)


def test_r2_p4_bug_colwidths_must_fail():
    # r2 第4頁實際值：width=11.93 但欄寬總和=2.95（REVIEW_R2 V2）
    with pytest.raises(ValueError, match='colwidths sum'):
        validate([['A', 'B', 'C'], ['1', '2', '3']], [.55, 1.20, 1.20], [.40, .95], 11.93)


def test_column_count_mismatch_fails():
    with pytest.raises(ValueError, match='columns'):
        validate(ROWS3, [3.0, 3.0], [.4, 1.0, 1.0], 6.0)


def test_row_count_mismatch_fails():
    with pytest.raises(ValueError, match='rows'):
        validate(ROWS3, [3.0, 3.0, 3.0], [.4, 1.0], 9.0)


def test_truncated_width_far_from_nominal_fails():
    with pytest.raises(ValueError, match='colwidths sum'):
        validate(ROWS3, [1.0, 1.0, 1.0], [.4, 1.0, 1.0], 11.93)

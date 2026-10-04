# -*- coding: utf-8 -*-
"""製作工具測試（D44 收尾輪版；放製作目錄，不動產品 tests/）。

執行：.venv/Scripts/python.exe -m pytest slides/source/test_make_tools.py -q
覆蓋：來源表數值（含 purge 期限別分組）、slide_id 映射、MD/PPT notes 同源、
架構頁語意標籤（五群組/箭頭/端點）、缺圖失敗、防覆寫、頁數一致、
PowerPoint 共享實例不得 Quit、缺 UI 截圖必須受控失敗。
"""
import argparse
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUN3 = ROOT / "outputs/proposal_delivery/run3_20261004_01"
PPTX_V3 = ROOT / "slides/TW01_菜價預測_研究提案與初步成果_v3.pptx"
PDF_V3 = PPTX_V3.with_suffix(".pdf")
NOTES_JSON = ROOT / "slides/source/notes_v3.json"
STATS = RUN3 / "stats_master.json"


def norm(text: str) -> str:
    return "".join(text.split())


class TestStatsMaster:
    def test_official_counts_match_resume_audit(self):
        d = json.loads(STATS.read_text(encoding="utf-8"))["descriptive"]
        expect = {
            "h7|ALL": (1149, 10952, "10.5%"), "h14|ALL": (1773, 10680, "16.6%"),
            "h7|cabbage": (227, 3357, "6.8%"), "h14|cabbage": (420, 3274, "12.8%"),
            "h7|bok_choy": (443, 3826, "11.6%"), "h14|bok_choy": (682, 3735, "18.3%"),
            "h7|sponge_gourd": (479, 3769, "12.7%"), "h14|sponge_gourd": (671, 3671, "18.3%"),
        }
        for k, (num, den, disp) in expect.items():
            assert d[k]["nonflat"] == num and d[k]["n"] == den and d[k]["percent_display"] == disp, k

    def test_float_boundary_note(self):
        m = json.loads(STATS.read_text(encoding="utf-8"))
        assert m["float_boundary_note"]["h7"]["minus_label"] == 7
        assert m["float_boundary_note"]["h14"]["minus_label"] == 14

    def test_purge_segments_by_horizon(self):
        p = json.loads(STATS.read_text(encoding="utf-8"))["purge"]
        assert p["rows"] == 1386 and p["distinct_t"] == 30
        seg = p["segments"]
        assert seg["train_to_val"]["h7"] == {"t_min": "2026-05-02", "t_max": "2026-05-09", "dates": 8, "rows": 242}
        assert seg["train_to_val"]["h14"] == {"t_min": "2026-04-25", "t_max": "2026-05-09", "dates": 15, "rows": 453}
        assert seg["val_to_test"]["h7"] == {"t_min": "2026-07-14", "t_max": "2026-07-21", "dates": 8, "rows": 243}
        assert seg["val_to_test"]["h14"] == {"t_min": "2026-07-07", "t_max": "2026-07-21", "dates": 15, "rows": 448}
        assert "t+h+1" in p["maturity_rule"]


class TestNotesSource:
    def test_19_slides_p01_to_p19(self):
        data = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
        ids = [s["slide_id"] for s in data["slides"]]
        assert ids == [f"p{i:02d}" for i in range(1, 20)]
        assert sum(1 for s in data["slides"] if s["kind"] == "main") == 15

    def test_every_slide_has_script_and_sources(self):
        for s in json.loads(NOTES_JSON.read_text(encoding="utf-8"))["slides"]:
            assert len(s["script"]) >= 30, s["slide_id"]
            assert s.get("sources"), s["slide_id"]

    def test_main_seconds_total(self):
        data = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
        assert sum(s["seconds"] for s in data["slides"] if s["kind"] == "main") == 690


class TestSlideNotesMdSameSource:
    def test_md_contains_all_normalized_scripts(self):
        md = norm((ROOT / "docs/SLIDE_NOTES.md").read_text(encoding="utf-8"))
        for s in json.loads(NOTES_JSON.read_text(encoding="utf-8"))["slides"]:
            assert norm(s["script"]) in md, s["slide_id"]


class TestPptxNotesSameSource:
    def test_pptx_notes_contain_normalized_scripts(self):
        from pptx import Presentation
        prs = Presentation(str(PPTX_V3))
        slides = list(prs.slides)
        assert len(slides) == 19
        data = json.loads(NOTES_JSON.read_text(encoding="utf-8"))
        for s, rec in zip(slides, data["slides"]):
            note = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
            assert norm(rec["script"]) in norm(note), rec["slide_id"]
            for src in rec["sources"]:
                assert norm(src) in norm(note), (rec["slide_id"], src)


class TestArchitectureSlideSemantics:
    """架構頁以語意驗收（教授正例：分群＋編號＋可對照），非僅以箭頭數量判定。"""

    def _texts(self):
        from pptx import Presentation
        prs = Presentation(str(PPTX_V3))
        arch = list(prs.slides)[7]  # p08
        return "\n".join(sh.text_frame.text for sh in arch.shapes if sh.has_text_frame)

    def test_five_numbered_groups_present(self):
        t = self._texts()
        for g in ["① 使用者與手機介面", "② 查詢處理", "③ 菜價計算", "④ 公開行情", "⑤ 預測紀錄"]:
            assert g in t, g

    def test_endpoints_present(self):
        t = self._texts()
        for ep in ["/forecast", "/agent/query", "/records"]:
            assert ep in t, ep

    def test_arrow_semantic_labels_present(self):
        t = norm(self._texts())
        for lab in ["提交查詢", "呼叫預測", "讀取歷史", "唯讀", "回傳結果", "期限・截止日", "保存當次", "查閱／", "匯出紀錄"]:
            assert norm(lab) in t, lab

    def test_readonly_and_private_storage_marked(self):
        t = self._texts()
        assert "唯讀" in t and "private/predictions" in t and "與④分離" in t

    def test_future_zone_and_legend(self):
        t = self._texts()
        assert "暫緩未來" in t and "不是用 LLM 猜菜價" in t
        assert "群組索引" in t and "非執行順序" in t

    def test_connectors_exist_as_visual_links(self):
        from pptx import Presentation
        from pptx.oxml.ns import qn
        prs = Presentation(str(PPTX_V3))
        arch = list(prs.slides)[7]
        assert len(arch.shapes._spTree.findall(qn("p:cxnSp"))) >= 7


class TestDeliverableCounts:
    def test_pdf_pages_equal_19(self):
        from pypdf import PdfReader
        assert len(PdfReader(str(PDF_V3)).pages) == 19

    def test_render_meta_match(self):
        meta = json.loads((RUN3 / "slides_render_v3/render_meta.json").read_text(encoding="utf-8"))
        assert meta["match"] is True and meta["pptx_slides"] == 19


class TestSafetyBehaviors:
    def test_make_assets_refuse_overwrite(self, tmp_path):
        (tmp_path / "x.png").write_bytes(b"1")
        r = subprocess.run([sys.executable, str(ROOT / "slides/source/make_assets.py"),
                            "--out", str(tmp_path), "--stats", str(STATS)],
                           capture_output=True, text=True)
        assert r.returncode == 2 and "REFUSE" in r.stderr

    def test_make_pptx_missing_asset_fails(self, tmp_path):
        empty = tmp_path / "empty_assets"
        empty.mkdir()
        r = subprocess.run([sys.executable, str(ROOT / "slides/source/make_pptx.py"),
                            "--pptx", str(tmp_path / "t.pptx"), "--assets", str(empty),
                            "--notes", str(NOTES_JSON), "--stats", str(STATS)],
                           capture_output=True, text=True)
        assert r.returncode == 3 and "缺圖" in r.stderr

    def test_make_pptx_missing_ui_shot_fails(self, tmp_path):
        """六張圖表齊備、但 UI 截圖不存在 → 必須受控失敗（不得輸出缺圖頁卻標成功）。"""
        r = subprocess.run([sys.executable, str(ROOT / "slides/source/make_pptx.py"),
                            "--pptx", str(tmp_path / "t.pptx"), "--assets", str(ROOT / "slides/assets_v3"),
                            "--notes", str(NOTES_JSON), "--stats", str(STATS),
                            "--ui-shot", str(tmp_path / "no_such_ui.png")],
                           capture_output=True, text=True)
        assert r.returncode == 3 and "UI 截圖" in r.stderr, (r.returncode, r.stderr[-300:])

    def test_make_pptx_refuse_overwrite_existing(self):
        r = subprocess.run([sys.executable, str(ROOT / "slides/source/make_pptx.py"),
                            "--pptx", str(PPTX_V3), "--assets", str(ROOT / "slides/assets_v3"),
                            "--notes", str(NOTES_JSON), "--stats", str(STATS)],
                           capture_output=True, text=True)
        assert r.returncode == 2 and "REFUSE" in r.stderr

    def test_v1_v2_outputs_untouched(self):
        import hashlib
        rec = json.loads((RUN3 / "protected_before.json").read_text(encoding="utf-8"))
        for key in ["slides/TW01_菜價預測_研究提案與初步成果_v1.pptx", "slides/TW01_菜價預測_研究提案與初步成果_v2.pptx"]:
            h = hashlib.sha256((ROOT / key).read_bytes()).hexdigest()
            assert rec[key]["sha256"] == h, key


class TestExportSafety:
    def test_shared_powerpoint_not_quit(self, tmp_path, monkeypatch):
        """模擬使用者已有簡報的共享 PowerPoint：只可 Close 本輪簡報，不得 Quit 應用（不啟真 COM）。"""
        fake_pptx = tmp_path / "x.pptx"
        fake_pptx.write_bytes(b"placeholder")
        closed = {"pres": False}

        class FakeSlideCollection:
            Count = 19

            def __call__(self, i):
                return types.SimpleNamespace(Export=lambda *a, **k: None)

        class FakePres:
            Slides = FakeSlideCollection()

            def SaveAs(self, *a, **k):
                (tmp_path / "out.pdf").write_bytes(b"pdf")

            def Close(self):
                closed["pres"] = True

        class FakePresentations:
            @property
            def Count(self):
                return 2  # 使用者簡報 + 本輪簡報

            def Open(self, *a, **k):
                return FakePres()

        class FakeApp:
            def __init__(self):
                self.presentations = FakePresentations()
                self.quit_called = False

            @property
            def Presentations(self):
                return self.presentations

            def Quit(self):
                self.quit_called = True

        app = FakeApp()
        fake_mod = types.ModuleType("win32com.client")
        fake_mod.Dispatch = lambda name: app
        fake_parent = types.ModuleType("win32com")
        fake_parent.client = fake_mod  # import a.b 不會重設 parent 屬性，需手動綁定
        monkeypatch.setitem(sys.modules, "win32com", fake_parent)
        monkeypatch.setitem(sys.modules, "win32com.client", fake_mod)
        fake_res = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"POWERPNT.EXE  1234  Console")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake_res)
        monkeypatch.setattr(argparse.ArgumentParser, "parse_args",
                            lambda self, *a, **k: argparse.Namespace(
                                pptx=str(fake_pptx), pdf=str(tmp_path / "out.pdf"),
                                render=str(tmp_path / "rd"), force=False))
        sys.path.insert(0, str(ROOT / "slides/source"))
        try:
            import export_and_render as er
            import importlib
            importlib.reload(er)
            er.main()
        finally:
            sys.path.remove(str(ROOT / "slides/source"))
        assert closed["pres"] is True, "本輪簡報應被 Close"
        assert not app.quit_called, "共享 PowerPoint 不得被 Quit"

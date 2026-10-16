"""Form must have no chat DOM/network; preserve A/B and records UI hooks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_form_no_agent_initialization_and_records_preserved():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    for banned in ("agentSection", "agentQuery", "agentBtn", "agentStatus"):
        assert banned not in html
    for banned in ("agent/query", "agent/status", "bindAgent(", "loadAgentStatus("):
        assert banned not in js
    for needed in ("predictForm", "hasLastWeek", "prevDate", "priceUnit", "obsDate",
                   "saveRecordBtn", "recordsPanel", "recordsList", "exportRecords"):
        assert needed in html
    for needed in ("tw01_ui_prefs_v1", "bindSaveAndRecords(", "lastRun",
                   "resetSaveBar(", "loadRecords(", "deleteRecord(", "mode: usePrev"):
        assert needed in js


def test_poisoned_frontend_source_detected():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    def is_safe(contents):
        return all(token not in contents for token in ("agent/query", "agent/status", "bindAgent("))
    assert is_safe(js)
    assert not is_safe(js + "\nfetch('agent/status')\n")

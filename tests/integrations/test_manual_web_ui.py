"""Form must have no chat DOM/network; preserve A/B and records UI hooks."""
from pathlib import Path
import shutil
import subprocess

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
    for needed in ("fmpa_ui_prefs_v1", "bindSaveAndRecords(", "lastRun",
                   "resetSaveBar(", "loadRecords(", "deleteRecord(", "mode: usePrev"):
        assert needed in js


def test_poisoned_frontend_source_detected():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    def is_safe(contents):
        return all(token not in contents for token in ("agent/query", "agent/status", "bindAgent("))
    assert is_safe(js)
    assert not is_safe(js + "\nfetch('agent/status')\n")


def test_prefs_migrate_once_from_legacy_key_and_keep_it():
    node = shutil.which("node")
    assert node, "Node is required for the frontend checks"
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    keys = js[js.index("const STORAGE_KEY ="):js.index("const DEFAULT_STORE_ID")]
    functions = js[js.index("function migrateStorageKey("):js.index("function savePrefs(")]
    harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const store = new Map([['tw01_ui_prefs_v1', '{"store_id":"store-legacy"}']]);
const context = {localStorage: {getItem: k => store.has(k) ? store.get(k) : null,
                                setItem: (k, v) => store.set(k, v)}};
vm.createContext(context);
vm.runInContext(SOURCE, context);
assert.equal(vm.runInContext('loadPrefs().store_id', context), 'store-legacy');
assert.equal(store.get('fmpa_ui_prefs_v1'), '{"store_id":"store-legacy"}');
assert.ok(store.has('tw01_ui_prefs_v1'), 'legacy key kept for rollback');
store.set('fmpa_ui_prefs_v1', '{"store_id":"store-new"}');
assert.equal(vm.runInContext('loadPrefs().store_id', context), 'store-new',
  'an existing new-key value is never overwritten by the legacy one');
"""
    harness = harness.replace("SOURCE", repr(keys + functions))
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr

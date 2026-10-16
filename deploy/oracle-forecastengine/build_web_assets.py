"""Rebuild a remote web variant without editing the existing Windows website.

Remote record saving is deliberately browser-local, never Oracle disk/private/.
Native server-side A/B prediction runs behind Nginx Basic Auth. The original
Windows Web A/B and server-side /records endpoints remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "web"

LOCAL_RECORDS_IMPL = r"""
const REMOTE_RECORDS_KEY = 'fmpa_web_browser_only_records_v1';
// Pre-rename key: copied once while the new key is absent; kept for rollback.
const LEGACY_REMOTE_RECORDS_KEY = 'tw01_web_browser_only_records_v1';

function readBrowserRecords() {
  try {
    if (localStorage.getItem(REMOTE_RECORDS_KEY) === null) {
      const legacy = localStorage.getItem(LEGACY_REMOTE_RECORDS_KEY);
      if (legacy !== null) localStorage.setItem(REMOTE_RECORDS_KEY, legacy);
    }
    const parsed = JSON.parse(localStorage.getItem(REMOTE_RECORDS_KEY) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function writeBrowserRecords(records) {
  localStorage.setItem(REMOTE_RECORDS_KEY, JSON.stringify(records.slice(0, 100)));
}

async function saveCurrentRecord() {
  if (!lastRun || !lastRun.response || lastRun.response.error) {
    setSaveStatus('請先完成有效的預測查詢。', true);
    return;
  }
  const btn = $('saveRecordBtn');
  btn.disabled = true;
  try {
    const records = readBrowserRecords();
    const resp = lastRun.response;
    const horizons = resp.results_without_last_week && resp.results_without_last_week.length
      ? resp.results_without_last_week : (resp.results || []);
    const record = {
      record_id: window.crypto.randomUUID(),
      saved_at: new Date().toISOString(),
      crop_id: resp.crop_id,
      market_id: resp.market_id,
      mode_executed: resp.mode_executed,
      model_version: resp.model_version,
      horizons: horizons.map(r => ({
        horizon_days: r.horizon_days,
        target_date: r.target_date,
        direction: r.direction,
        relative_change_estimate: r.relative_change_estimate,
        price_estimate: r.price_estimate
      })),
      request: lastRun.request,
      response: resp,
      anonymous_store_label: ($('storeId').value || '').trim()
    };
    records.unshift(record);
    writeBrowserRecords(records);
    btn.textContent = '已保存於此瀏覽器';
    setSaveStatus('已儲存在此瀏覽器（不會傳送或保存到 Oracle；請定期匯出備份）。', false);
    if (recordsLoaded) loadRecords();
  } catch (_) {
    btn.disabled = false;
    setSaveStatus('瀏覽器本機儲存不可用或容量已滿；請使用匯出功能備份。', true);
  }
}

"""

LOCAL_RECORD_OPERATIONS = r"""
async function loadRecords() {
  recordsLoaded = true;
  setRecordsStatus('');
  renderRecords(readBrowserRecords());
}

async function deleteRecord(recordId, btn) {
  if (!recordId || !window.confirm('要從這個瀏覽器刪除這筆預測紀錄嗎？')) return;
  btn.disabled = true;
  try {
    writeBrowserRecords(readBrowserRecords().filter(r => r.record_id !== recordId));
    await loadRecords();
  } catch (_) {
    btn.disabled = false;
    setRecordsStatus('刪除失敗；瀏覽器儲存功能可能不可用。');
  }
}

function exportBrowserRecords(event) {
  event.preventDefault();
  const bytes = JSON.stringify({saved_at: new Date().toISOString(),
    storage_scope: 'this_browser_only',
    records: readBrowserRecords()}, null, 2);
  const url = URL.createObjectURL(new Blob([bytes], {type:'application/json'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'fmpa_oracle_browser_only_records.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

"""


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Expected exactly one pattern (found {count}): {old[:70]}")
    return text.replace(old, new)


def build(dst: Path):
    if dst.exists():
        raise FileExistsError("Never overwrite an existing web asset release")
    html = (SOURCE / "index.html").read_text(encoding="utf-8")
    js = (SOURCE / "app.js").read_text(encoding="utf-8")
    css = (SOURCE / "style.css").read_text(encoding="utf-8")

    html = replace_once(
        html,
        "手動輸入現場價格，比較 7／14 天 A／B 推估；無須登入或連線語言模型",
        "透過安全 HTTPS 登入，輸入店價即可取得 7／14 天 A／B 推估；不依賴語言模型",
    )
    html = replace_once(
        html,
        "匿名識別碼會隨查詢送到本機 API；只有按保存才會寫入本機紀錄。格式例如 store-a。",
        "僅用於本瀏覽器本機標記，**不會**送到 Oracle，也不會同步 Windows 紀錄。格式例如 store-a。",
    )
    html = replace_once(
        html,
        "自願保存這次預測到伺服器，之後可單筆刪除或全部匯出；不保存、關閉頁面都不影響查詢。",
        "按保存後只會存在**目前瀏覽器**的本機儲存空間，不會存於 Oracle／Windows；請定期匯出備份。",
    )
    html = replace_once(
        html,
        "只有按過「保存這次預測」的查詢才會出現在這裡（匿名摘要）。",
        "僅此瀏覽器已保存的紀錄；不與 Windows 原有私人紀錄同步。清除瀏覽器資料時可能消失，請主動匯出。",
    )
    html = replace_once(
        html,
        'href="records/export" download="fmpa_prediction_records.json"',
        'href="#" download="fmpa_oracle_browser_only_records.json"',
    )
    html = replace_once(
        html,
        '<footer>',
        '<p class="hint">隱私：輸入價格與選填上週價會經 HTTPS 送至本服務計算，不在 Oracle 端保存；'
        '本頁保存紀錄只存在此瀏覽器。Windows 原始 Web A/B 與本機紀錄仍各自保留。</p>\n'
        '    <footer>',
    )
    js = replace_once(
        js,
        "if (storeId) body.store_id = storeId;",
        "// Anonymous store label never leaves this browser.",
    )
    js = replace_once(
        js,
        "$('obsDate').value = toInputDate(new Date());",
        "$('obsDate').value = taipeiToday();",
    )
    js = replace_once(
        js,
        "function nowInputTime() {\n  const d = new Date();\n  return pad2(d.getHours()) + ':' + pad2(d.getMinutes());\n}",
        "function nowInputTime() {\n"
        "  return new Intl.DateTimeFormat('en-GB', {\n"
        "    timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hour12: false\n"
        "  }).format(new Date());\n"
        "}\n"
        "\nfunction taipeiToday() {\n"
        "  const parts = new Intl.DateTimeFormat('en-US', {\n"
        "    timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit'\n"
        "  }).formatToParts(new Date());\n"
        "  const value = Object.fromEntries(parts.map(p => [p.type, p.value]));\n"
        "  return value.year + '-' + value.month + '-' + value.day;\n"
        "}",
    )
    js = replace_once(
        js,
        "if (date && date > toInputDate(new Date())) {",
        "if (date && date > taipeiToday()) {",
    )
    start = js.index("async function saveCurrentRecord() {")
    end = js.index("function setRecordsStatus(", start)
    js = js[:start] + LOCAL_RECORDS_IMPL + js[end:]
    start = js.index("async function loadRecords() {")
    end = js.index("function bindSaveAndRecords() {", start)
    js = js[:start] + LOCAL_RECORD_OPERATIONS + js[end:]
    js = replace_once(
        js,
        "if (saveBtn) saveBtn.addEventListener('click', saveCurrentRecord);",
        "if (saveBtn) saveBtn.addEventListener('click', saveCurrentRecord);\n"
        "  const exportLink = $('exportRecords');\n"
        "  if (exportLink) exportLink.addEventListener('click', exportBrowserRecords);",
    )
    if any(word in js for word in (
        "fetchJson(API_RECORDS", "API_RECORDS + '/'",
        "body: JSON.stringify({ request_id: lastRun.response.request_id })",
        "agent/query",
    )):
        raise RuntimeError("Remote frontend retained a forbidden record/agent HTTP route")
    dst.mkdir(parents=True)
    for filename, text in {"index.html": html, "app.js": js, "style.css": css}.items():
        (dst / filename).write_text(text, encoding="utf-8")
    summary = {
        "assets": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.iterdir()},
        "source_originals_not_modified": True,
        "oracle_server_private_record_write": False,
    }
    print(summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)

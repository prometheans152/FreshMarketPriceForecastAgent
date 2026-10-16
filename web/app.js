'use strict';

/* =========================================================
 * TW01 現場菜價預測 — 手機網頁（T21）
 * 純靜態、無外部 CDN 依賴、無追蹤。
 * API 為同源相對路徑（部署時 API server 直接 serve web/）。
 * 欄位語意依 contracts/forecast.schema.json。
 * 表單回應直接來自 ForecastEngine
 * 與 /records 保存端點，依後端契約實作（ROUND2 審查 F07/F08 修復）。
 * =======================================================*/

// API 路徑（同源、相對路徑；不加前導斜線，頁面與 API 同目錄即可作用）
const API_FORECAST = 'forecast';
const API_RECORDS = 'records';
const API_RECORDS_EXPORT = 'records/export';

// 內建品項（對應 configs/project.yaml crops.first_version）
const CROPS = [
  { id: 'cabbage', label: '甘藍（平地高麗菜）' },
  { id: 'bok_choy', label: '青江白菜' },
  { id: 'sponge_gourd', label: '絲瓜' }
];

// 內建臺中參考市場（臺中公開來源之標準化市場名稱；不含停用的 (停)建國市場）
const MARKETS = [
  '中義市場', '南屯市場', '合作市場', '大甲第二市場', '東光市場',
  '梧棲第一市場', '沙鹿市場', '清水第一市場', '第三市場', '第二市場',
  '第五市場', '豐原第一市場', '霧峰市場'
];

// 可輸入單位（configs accepted_input_units；顆／把／袋屬不可比單位，不提供輸入）
const INPUT_UNITS = [
  { id: 'NTD_per_taiwan_jin', label: '元／台斤' },
  { id: 'NTD_per_kg', label: '元／公斤' }
];

// 回應單位的顯示名稱（含不可比單位，僅用於顯示）
const UNIT_LABELS = {
  NTD_per_taiwan_jin: '元／台斤',
  NTD_per_kg: '元／公斤',
  per_piece: '元／顆',
  per_bunch: '元／把',
  per_bag: '元／袋',
  unknown: '未知單位'
};

const DIRECTION_INFO = {
  up: { label: '上漲', arrow: '▲' },
  flat: { label: '持平', arrow: '—' },
  down: { label: '下跌', arrow: '▼' },
  insufficient_data: { label: '資料不足', arrow: '？' }
};

const TARGET_SCOPE_LABELS = {
  market_mean: '市場均價',
  store_price_estimate: '店價估計'
};

const VALIDATION_SCOPE_LABELS = {
  public_market_test: '公開市場測試',
  store_pilot: '指定店試點',
  unvalidated: '尚未驗證'
};

const STORAGE_KEY = 'tw01_ui_prefs_v1';
const DEFAULT_STORE_ID = 'store-a';
const STORE_ID_RE = /^[A-Za-z0-9_-]+$/;

class ApiError extends Error {
  constructor(message, code) {
    super(message);
    this.code = code || null;
  }
}

/* ---------- 小工具 ---------- */

const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function pad2(n) {
  return String(n).padStart(2, '0');
}

function toInputDate(d) {
  return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
}

function nowInputTime() {
  const d = new Date();
  return pad2(d.getHours()) + ':' + pad2(d.getMinutes());
}

function addDays(dateStr, days) {
  const parts = dateStr.split('-').map(Number);
  const d = new Date(parts[0], parts[1] - 1, parts[2] + days);
  return toInputDate(d);
}

function fmtChange(r) {
  if (r == null) return '—';
  const pct = r * 100;
  const sign = pct > 0 ? '+' : (pct < 0 ? '−' : '');
  return sign + Math.abs(pct).toFixed(1) + '%';
}

function fmtPrice(p, unit) {
  if (p == null) return '—';
  const num = Number.isInteger(p) ? String(p) : Number(p).toFixed(1);
  const unitLabel = UNIT_LABELS[unit] || '（未知單位）';
  return num + ' ' + unitLabel;
}

function cropLabel(cropId) {
  const found = CROPS.filter((c) => c.id === cropId)[0];
  return found ? found.label : cropId;
}

// 共用 fetch＋JSON 解析；連線失敗統一轉為 ApiError（使用者可懂訊息）
async function fetchJson(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new ApiError('無法連線到伺服器，請確認服務已啟動或網路狀況。', null);
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (err) {
      data = null;
    }
  }
  return { res: res, data: data };
}

/* ---------- localStorage（只記選項與匿名店號，不記價格） ---------- */

function loadPrefs() {
  let prefs = null;
  try {
    prefs = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
  } catch (err) {
    prefs = null;
  }
  return prefs && typeof prefs === 'object' ? prefs : {};
}

function savePrefs() {
  const prefs = {
    crop_id: $('crop').value,
    market_id: $('market').value,
    price_unit: $('priceUnit').value,
    store_id: $('storeId').value.trim()
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (err) {
    /* 無痕模式等情境寫入失敗時忽略，不影響查詢 */
  }
}

/* ---------- 店號單一來源（F07） ----------
 * 表單 #storeId 是唯一來源（初始值來自 tw01_ui_prefs_v1）；
 * 本機表單匿名店號，不涉及聊天。 */
function currentStoreId() {
  const input = $('storeId');
  const value = input ? input.value.trim() : '';
  if (value) return value;
  return loadPrefs().store_id || DEFAULT_STORE_ID;
}

/* ---------- 表單初始化 ---------- */

function fillSelect(sel, items, selected) {
  sel.innerHTML = '';
  items.forEach((item) => {
    const value = typeof item === 'string' ? item : item.id;
    const label = typeof item === 'string' ? item : item.label;
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = label;
    if (value === selected) opt.selected = true;
    sel.appendChild(opt);
  });
}

function init() {
  const prefs = loadPrefs();

  fillSelect($('crop'), CROPS, prefs.crop_id || CROPS[0].id);
  fillSelect($('market'), MARKETS, prefs.market_id || MARKETS[0]);
  fillSelect($('priceUnit'), INPUT_UNITS, prefs.price_unit || INPUT_UNITS[0].id);
  fillSelect($('prevUnit'), INPUT_UNITS, $('priceUnit').value);
  $('storeId').value = prefs.store_id || DEFAULT_STORE_ID;
  $('obsDate').value = toInputDate(new Date());
  $('obsTime').value = nowInputTime();

  // 上週單位預設同今天；改今天單位時自動同步（不同單位不可比）
  $('priceUnit').addEventListener('change', () => {
    $('prevUnit').value = $('priceUnit').value;
  });

  // 上週區塊開關：第一次打開時，預設帶入「觀察日期 −7 天」
  $('hasLastWeek').addEventListener('change', () => {
    const on = $('hasLastWeek').checked;
    $('prevWeekPanel').hidden = !on;
    if (on && !$('prevDate').value) {
      const base = $('obsDate').value || toInputDate(new Date());
      $('prevDate').value = addDays(base, -7);
    }
  });

  $('predictForm').addEventListener('submit', onSubmit);
  bindSaveAndRecords();
}

/* ---------- 請求組裝與驗證 ---------- */

function buildRequest() {
  const errors = [];

  const cropId = $('crop').value;
  const marketId = $('market').value;
  const priceRaw = $('currentPrice').value.trim();
  const unit = $('priceUnit').value;
  const date = $('obsDate').value;
  const time = $('obsTime').value || '00:00';
  const storeId = $('storeId').value.trim();

  if (!cropId) errors.push('請選擇品項');
  if (!marketId) errors.push('請選擇參考市場');

  const price = Number.parseFloat(priceRaw);
  if (!priceRaw || !Number.isFinite(price) || price <= 0) {
    errors.push('請輸入有效的今天價格（須大於 0）');
  }
  if (!date) errors.push('請填寫觀察日期');
  if (date && date > toInputDate(new Date())) {
    errors.push('觀察日期不可在未來');
  }
  if (!time) errors.push('請填寫觀察時間');
  if (storeId && !STORE_ID_RE.test(storeId)) {
    errors.push('匿名店號僅能使用英文、數字、- 與 _（例如 store-a）');
  }

  const usePrev = $('hasLastWeek').checked;
  let prevPrice = null;
  let prevDate = null;
  let prevUnit = null;

  if (usePrev) {
    const prevRaw = $('prevPrice').value.trim();
    prevPrice = Number.parseFloat(prevRaw);
    if (!prevRaw || !Number.isFinite(prevPrice) || prevPrice <= 0) {
      errors.push('請輸入有效的上週價格（須大於 0）');
    }
    prevDate = $('prevDate').value;
    if (!prevDate) errors.push('請填寫上週實際日期');
    prevUnit = $('prevUnit').value || unit;
  }

  if (errors.length) return { errors: errors };

  const body = {
    crop_id: cropId,
    market_id: marketId,
    current_price: price,
    price_unit: unit,
    observed_at: date + 'T' + time + ':00+08:00',
    mode: usePrev ? 'both' : 'without_last_week'
  };
  if (storeId) body.store_id = storeId;
  if (usePrev) {
    body.previous_price = prevPrice;
    body.previous_observed_at = prevDate + 'T00:00:00+08:00';
    body.previous_price_unit = prevUnit;
  }
  return { body: body };
}

/* ---------- 送出與錯誤處理 ---------- */

function showError(message, code) {
  const el = $('errorBox');
  const codeHtml = code ? '<span class="err-code">' + esc(code) + '</span>' : '';
  el.innerHTML = codeHtml + esc(message);
  el.hidden = false;
}

function clearError() {
  const el = $('errorBox');
  el.hidden = true;
  el.textContent = '';
}

function setLoading(loading) {
  const btn = $('predictBtn');
  btn.disabled = loading;
  btn.textContent = loading ? '查詢中…' : '查詢預測';
}

async function onSubmit(event) {
  event.preventDefault();
  clearError();
  $('result').innerHTML = '';
  hideSaveBar();

  const built = buildRequest();
  if (built.errors) {
    showError(built.errors.join('；'));
    return;
  }

  setLoading(true);
  try {
    const res = await fetch(API_FORECAST, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(built.body)
    });

    let data = null;
    const text = await res.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (err) {
        data = null;
      }
    }

    if (!res.ok) {
      const err = data && data.error ? data.error : null;
      const message = err && err.message ? err.message : '伺服器回應錯誤（HTTP ' + res.status + '）';
      throw new ApiError(message, err ? err.code : null);
    }
    if (!data) {
      throw new ApiError('伺服器回應不是有效的 JSON，無法解讀結果。');
    }
    if (data.error && data.error.message) {
      // 200 但帶 error 物件（例如 unsupported_crop、non_comparable_unit）
      showError(data.error.message, data.error.code);
      return;
    }
    if (!Array.isArray(data.results) && !Array.isArray(data.results_without_last_week)) {
      showError('伺服器回應缺少預測結果。');
      return;
    }

    renderResponse(data);
    savePrefs();
    lastRun = { request: built.body, response: data, source: 'form' };
    resetSaveBar();
    setSaveStatus('本列保存的是剛才的表單查詢結果。', false);
  } catch (err) {
    if (err instanceof ApiError) {
      showError(err.message, err.code);
    } else {
      showError('無法連線到伺服器，請確認服務已啟動或網路狀況。');
    }
  } finally {
    setLoading(false);
  }
}

/* ---------- 結果呈現 ---------- */

function horizonCard(result, modeTag) {
  const known = Object.prototype.hasOwnProperty.call(DIRECTION_INFO, result.direction);
  const dir = known ? DIRECTION_INFO[result.direction] : { label: String(result.direction), arrow: '？' };
  const dirCls = 'dir-' + (known ? result.direction : 'na');

  const scopeParts = [];
  if (result.target_scope && TARGET_SCOPE_LABELS[result.target_scope]) {
    scopeParts.push(TARGET_SCOPE_LABELS[result.target_scope]);
  }
  if (result.validation_scope && VALIDATION_SCOPE_LABELS[result.validation_scope]) {
    scopeParts.push('驗證：' + VALIDATION_SCOPE_LABELS[result.validation_scope]);
  }

  const warningsHtml = (result.warnings || [])
    .map((w) => '<li>⚠ ' + esc(w) + '</li>')
    .join('');

  const modeChip = modeTag
    ? '<span class="chip ' + esc(modeTag.cls) + '">' + esc(modeTag.text) + '</span>'
    : '';

  return '' +
    '<article class="card">' +
      '<div class="card-top">' +
        '<span class="chip">' + esc(result.horizon_days) + ' 天後</span>' + modeChip +
      '</div>' +
      '<p class="target-date">到期日 ' + esc(result.target_date) + '</p>' +
      '<p class="dir ' + dirCls + '"><span class="arrow">' + dir.arrow + '</span>' + esc(dir.label) + '</p>' +
      '<dl class="nums">' +
        '<div><dt>相對變化</dt><dd>' + esc(fmtChange(result.relative_change_estimate)) + '</dd></div>' +
        '<div><dt>價格估計</dt><dd>' + esc(fmtPrice(result.price_estimate, result.price_estimate_unit)) + '</dd></div>' +
      '</dl>' +
      (scopeParts.length ? '<p class="scope-note">' + esc(scopeParts.join('・')) + '</p>' : '') +
      (warningsHtml ? '<ul class="warnings">' + warningsHtml + '</ul>' : '') +
    '</article>';
}

// 把 ForecastResponse 渲染成 HTML 字串（主表單與代理人結構化結果卡共用；全部經 esc()）
function forecastHtml(data) {
  const parts = [];

  // 查詢條件回顧
  const echoBits = [];
  if (data.crop_id) echoBits.push(cropLabel(data.crop_id));
  if (data.market_id) echoBits.push(data.market_id);
  if (data.input_observed_at) echoBits.push('觀察時間 ' + data.input_observed_at);
  if (echoBits.length) {
    parts.push('<p class="req-echo">' + esc(echoBits.join('・')) + '</p>');
  }

  // 執行模式說明
  const modeNotes = {
    without_last_week: '模式 A：未使用上週價（今天價＋公開行情）',
    with_last_week: '模式 B：使用上週價',
    both: 'A／B 對照：A 未用上週價，B 使用上週價',
    fallback_without_last_week: '上週資料不可比，自動改用模式 A'
  };
  const modeNote = modeNotes[data.mode_executed] || ('執行模式：' + data.mode_executed);
  parts.push('<p class="mode-note">' + esc(modeNote) + '</p>');
  parts.push('<p class="hint">下方原模型警示中的「今天」是本次填寫的報價基準日，不一定是查詢當日。</p>');

  // 全域警示逐條顯示
  if (Array.isArray(data.warnings) && data.warnings.length) {
    parts.push('<ul class="global-warnings">' +
      data.warnings.map((w) => '<li>⚠ ' + esc(w) + '</li>').join('') +
      '</ul>');
  }

  // 決定 A／B 結果清單
  let aList = null;
  let bList = null;
  let bReason = data.b_unavailable_reason || null;

  if (Array.isArray(data.results_without_last_week) && data.results_without_last_week.length) {
    aList = data.results_without_last_week;
    bList = Array.isArray(data.results_with_last_week) ? data.results_with_last_week : [];
    if (!bList.length && !bReason) {
      bReason = '上週資料不可比或不足，未提供 B 模式結果。';
    }
  } else {
    aList = Array.isArray(data.results) ? data.results : [];
  }

  const hasAB = aList && bList && bList.length > 0;

  if (hasAB) {
    // A／B 並排對照：每個期限一列，左 A 右 B
    [7, 14].forEach((h) => {
      const a = aList.filter((r) => r.horizon_days === h)[0];
      const b = bList.filter((r) => r.horizon_days === h)[0];
      if (!a && !b) return;
      const aHtml = a
        ? horizonCard(a, { text: 'A', cls: 'chip-a' })
        : '<p class="card empty-cell">無資料</p>';
      const bHtml = b
        ? horizonCard(b, { text: 'B', cls: 'chip-b' })
        : '<p class="card empty-cell">未提供</p>';
      parts.push('<div class="ab-row"><div class="ab-cell">' + aHtml + '</div><div class="ab-cell">' + bHtml + '</div></div>');
    });
    if (bReason) {
      parts.push('<p class="notice">部分期限 B 未提供：' + esc(bReason) + '</p>');
    }
  } else {
    // 單欄顯示；若 B 不可用，先講原因再顯示 A
    if (aList && bList && bReason) {
      parts.push('<div class="notice">B 模式不可用：' + esc(bReason) + '<br>以下僅顯示 A 模式結果。</div>');
    }
    const singleTag = data.mode_executed === 'with_last_week'
      ? { text: 'B', cls: 'chip-b' }
      : { text: 'A', cls: 'chip-a' };
    aList.forEach((r) => parts.push(horizonCard(r, singleTag)));
    if (!aList.length) {
      parts.push('<p class="empty-all">沒有取得任何預測結果。</p>');
    }
  }

  // 資料截止與版本小字
  const metaBits = [];
  if (data.public_data_cutoff) {
    const age = typeof data.public_data_age_days === 'number'
      ? '（' + data.public_data_age_days + ' 天前）'
      : '';
    metaBits.push('公開資料截止：' + data.public_data_cutoff + age);
  }
  if (data.model_version) metaBits.push('模型版本 ' + data.model_version);
  if (data.data_version) metaBits.push('資料版本 ' + data.data_version);
  if (metaBits.length) {
    parts.push('<p class="meta">' + metaBits.map(esc).join('｜') + '</p>');
  }

  return parts.join('');
}

function renderResponse(data) {
  $('result').innerHTML = forecastHtml(data);
}

/* ---------- 預測保存與紀錄（T22；使用者自願，預設不自動保存） ---------- */

let lastRun = null;        // 最近一次成功查詢：{ request, response }
let recordsLoaded = false; // 紀錄清單是否已載入過（展開面板時惰性載入）

function setSaveStatus(message, isError) {
  const el = $('saveStatus');
  if (!el) return;
  if (!message) {
    el.hidden = true;
    el.textContent = '';
    el.className = 'save-status';
    return;
  }
  el.textContent = message;
  el.className = 'save-status ' + (isError ? 'save-status-err' : 'save-status-ok');
  el.hidden = false;
}

function hideSaveBar() {
  lastRun = null;
  const bar = $('saveBar');
  if (!bar) return;
  bar.hidden = true;
  const btn = $('saveRecordBtn');
  if (btn) {
    btn.disabled = false;
    btn.textContent = '保存這次預測';
  }
  setSaveStatus(null);
}

function resetSaveBar() {
  const bar = $('saveBar');
  if (!bar) return;
  const btn = $('saveRecordBtn');
  if (btn) {
    btn.disabled = false;
    btn.textContent = '保存這次預測';
  }
  setSaveStatus(null);
  bar.hidden = false;
}

async function saveCurrentRecord() {
  if (!lastRun || !lastRun.response) {
    setSaveStatus('沒有可保存的預測，請先完成一次查詢。', true);
    return;
  }
  const btn = $('saveRecordBtn');
  btn.disabled = true;
  btn.textContent = '保存中…';
  try {
    const { res, data } = await fetchJson(API_RECORDS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: lastRun.response.request_id })
    });
    if (!res.ok || !data || data.ok !== true) {
      const msg = data && data.error && data.error.message
        ? data.error.message
        : '保存失敗（HTTP ' + res.status + '）；這次查詢結果不受影響。';
      setSaveStatus(msg, true);
      btn.disabled = false;
      btn.textContent = '保存這次預測';
      return;
    }
    setSaveStatus('已保存（編號 ' + (data.record_id || '—') + '，時間 ' + (data.saved_at || '—') + '）。', false);
    btn.textContent = '已保存';
    if (recordsLoaded) loadRecords();
  } catch (err) {
    setSaveStatus(err instanceof ApiError ? err.message : '保存失敗；這次查詢結果不受影響。', true);
    btn.disabled = false;
    btn.textContent = '保存這次預測';
  }
}

function setRecordsStatus(message) {
  const el = $('recordsStatus');
  if (!el) return;
  if (!message) {
    el.hidden = true;
    el.textContent = '';
    return;
  }
  el.textContent = message;
  el.hidden = false;
}

function recordModeLabel(mode) {
  const map = {
    without_last_week: '模式 A',
    with_last_week: '模式 B',
    both: 'A／B 對照',
    fallback_without_last_week: '上週不可比，自動改用 A'
  };
  return map[mode] || ('模式：' + mode);
}

function renderRecords(records) {
  const box = $('recordsList');
  if (!Array.isArray(records) || !records.length) {
    box.innerHTML = '<p class="records-empty">目前沒有已保存的紀錄。</p>';
    return;
  }
  box.innerHTML = records.map((r) => {
    const horizonBits = (r.horizons || []).map((h) => {
      const known = Object.prototype.hasOwnProperty.call(DIRECTION_INFO, h.direction);
      const dir = known ? DIRECTION_INFO[h.direction] : { label: String(h.direction), arrow: '？' };
      return h.horizon_days + ' 天後 ' + dir.arrow + dir.label + '（到期 ' + h.target_date + '）';
    }).join('・');
    return '' +
      '<article class="record-item">' +
        '<div class="record-main">' +
          '<p class="record-title">' + esc(r.crop_id ? cropLabel(r.crop_id) : '未知品項') +
            '・' + esc(r.market_id || '未記市場') + '</p>' +
          '<p class="record-meta">保存於 ' + esc(r.saved_at || '—') +
            '｜' + esc(recordModeLabel(r.mode_executed)) + '</p>' +
          (horizonBits ? '<p class="record-horizons">' + esc(horizonBits) + '</p>' : '') +
          (r.model_version ? '<p class="record-meta">模型版本 ' + esc(r.model_version) + '</p>' : '') +
        '</div>' +
        '<button type="button" class="danger small" data-record-id="' + esc(r.record_id) + '">刪除</button>' +
      '</article>';
  }).join('');
}

async function loadRecords() {
  const box = $('recordsList');
  if (!box) return;
  setRecordsStatus('');
  box.innerHTML = '<p class="records-empty">載入中…</p>';
  try {
    const { res, data } = await fetchJson(API_RECORDS, { method: 'GET' });
    if (!res.ok) {
      const msg = data && data.error && data.error.message
        ? data.error.message
        : '無法載入紀錄（HTTP ' + res.status + '）。';
      throw new ApiError(msg, null);
    }
    if (!data || !Array.isArray(data.records)) {
      throw new ApiError('伺服器回應格式不正確，無法解讀紀錄清單。', null);
    }
    recordsLoaded = true;
    renderRecords(data.records);
  } catch (err) {
    box.innerHTML = '';
    setRecordsStatus((err instanceof ApiError ? err.message : '無法載入紀錄，請稍後再試。') +
      '（查詢預測功能不受影響）');
  }
}

async function deleteRecord(recordId, btn) {
  if (!recordId) return;
  if (!window.confirm('要刪除這筆保存紀錄嗎？刪除後無法復原。')) return;
  btn.disabled = true;
  try {
    const { res, data } = await fetchJson(
      API_RECORDS + '/' + encodeURIComponent(recordId),
      { method: 'DELETE' }
    );
    if (!res.ok || !data || data.ok !== true) {
      const msg = data && data.error && data.error.message
        ? data.error.message
        : '刪除失敗（HTTP ' + res.status + '）。';
      throw new ApiError(msg, null);
    }
    await loadRecords();
  } catch (err) {
    btn.disabled = false;
    setRecordsStatus(err instanceof ApiError ? err.message : '刪除失敗，請稍後再試。');
  }
}

function bindSaveAndRecords() {
  const saveBtn = $('saveRecordBtn');
  if (saveBtn) saveBtn.addEventListener('click', saveCurrentRecord);

  const panel = $('recordsPanel');
  if (panel) {
    // 第一次展開「已保存紀錄」才載入（後端尚未提供端點時不影響其他功能）
    panel.addEventListener('toggle', () => {
      if (panel.open && !recordsLoaded) loadRecords();
    });
    const refresh = $('refreshRecords');
    if (refresh) refresh.addEventListener('click', loadRecords);
  }

  const list = $('recordsList');
  if (list) {
    list.addEventListener('click', (e) => {
      const btn = e.target && e.target.closest ? e.target.closest('button[data-record-id]') : null;
      if (!btn) return;
      deleteRecord(btn.getAttribute('data-record-id'), btn);
    });
  }
}

document.addEventListener('DOMContentLoaded', init);

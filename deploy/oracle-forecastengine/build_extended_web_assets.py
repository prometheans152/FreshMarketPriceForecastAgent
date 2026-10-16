"""Build grouped searchable 61-item website without editing Windows web files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_web_assets import replace_once

ROOT = Path(__file__).resolve().parents[2]
PARENT_RUN = ROOT / "outputs/quality_runs/oracle_web_preservation_20261014_182628_Windows5800X/site_v2"
CATEGORIES = ["vegetable", "fruit", "seafood", "meat", "egg"]

JS_CATALOG_CONTROLS = """
const CROP_CATEGORIES = [
  {id:'all',label:'全部 61 項'},
  {id:'vegetable',label:'蔬菜 15 項'},
  {id:'fruit',label:'水果 27 項'},
  {id:'seafood',label:'魚與海鮮 7 項'},
  {id:'meat',label:'肉類 10 項'},
  {id:'egg',label:'蛋類 2 項'}
];

function findSelectedCrop() {
  return CROPS.find(c => c.id === $('crop').value) || null;
}

function populateCrops(keepId) {
  const category = $('cropCategory').value;
  const search = ($('cropSearch').value || '').trim().toLocaleLowerCase('zh-Hant');
  const select = $('crop');
  const visible = CROPS.filter(c =>
    (category === 'all' || c.category === category) &&
    (!search || [c.label, c.id, ...(c.aliases || [])]
      .join(' ').toLocaleLowerCase('zh-Hant').includes(search)));
  select.innerHTML = '';
  for (const group of CROP_CATEGORIES.filter(x => x.id !== 'all')) {
    const items = visible.filter(x => x.category === group.id);
    if (!items.length) continue;
    const element = document.createElement('optgroup');
    element.label = group.label;
    items.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.label + (c.has_data ? '' : '（無有效行情）');
      opt.disabled = !c.has_data;
      opt.selected = (c.id === keepId) && c.has_data;
      element.appendChild(opt);
    });
    select.appendChild(element);
  }
  const options = Array.from(select.options);
  if (!options.some(x => x.selected && !x.disabled)) {
    const first = options.find(x => !x.disabled);
    if (first) select.value = first.value;
  }
  const status = $('cropStatus');
  if (!options.length) {
    status.textContent = '沒有符合條件的品項，請清除搜尋或更換分類。';
  } else {
    status.textContent = '目前篩選 ' + visible.length +
      ' 項（官方公開來源共 61 欄；並非所有菜都有價格）。';
  }
  updateCropMarketStatus();
}

function updateCropMarketStatus() {
  const crop = findSelectedCrop();
  const method = $('cropMethodStatus');
  const info = $('marketPriceStatus');
  const markets = $('market');
  if (!crop || !crop.has_data) {
    method.textContent = '此品項沒有有效公開行情，不能提供估計。';
    info.textContent = '';
    return;
  }
  method.textContent = crop.method === 'frozen_rf_hgb_v0.1.0'
    ? '此品項沿用原 RF／HGB 模型 v0.1.0；7／14 天估計仍未在同店到期驗證。'
    : '此品項使用「未訓練的歷史趨勢基準」，不是 RF／HGB 已訓練模型，也沒有真店準確度驗證。';
  const current = markets.value;
  for (const opt of Array.from(markets.options)) {
    const n = crop.markets[opt.value]?.observations || 0;
    opt.disabled = n === 0;
  }
  if (markets.selectedOptions.length === 0 || markets.selectedOptions[0].disabled) {
    const first = Array.from(markets.options).find(opt => !opt.disabled);
    if (first) markets.value = first.value;
  }
  const stat = crop.markets[markets.value];
  info.textContent = stat && stat.observations
    ? '參考 ' + markets.value + '：公開有效日價 ' + stat.observations +
      ' 筆；最近行情 ' + stat.latest_observed_date + ' ' +
      stat.latest_public_market_mean + ' 元／台斤。這不是今天的單店售價。'
    : '此市場沒有此品項有效公開價格；請更換市場。';
}

function setupCropCatalog() {
  fillSelect($('cropCategory'), CROP_CATEGORIES, 'all');
  $('cropCategory').addEventListener('change', () => populateCrops($('crop').value));
  $('cropSearch').addEventListener('input', () => populateCrops($('crop').value));
  $('crop').addEventListener('change', updateCropMarketStatus);
  $('market').addEventListener('change', updateCropMarketStatus);
  populateCrops(loadPrefs().crop_id || 'cabbage');
}
"""


def build(catalog_path: Path, output: Path):
    if output.exists():
        raise FileExistsError("Refuse to overwrite prior web assets")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if len(catalog["items"]) != 61:
        raise ValueError("61 public source item catalog expected")
    prior_html = (PARENT_RUN / "index.html").read_text(encoding="utf-8")
    prior_js = (PARENT_RUN / "app.js").read_text(encoding="utf-8")
    prior_css = (PARENT_RUN / "style.css").read_text(encoding="utf-8")

    data = []
    for c in catalog["items"]:
        data.append({
            "id": c["crop_id"],
            "label": c["display_name"],
            "category": c["category"],
            "aliases": c["aliases"],
            "method": c["method"],
            "has_data": c["has_ever_had_public_price"],
            "markets": c["markets"],
        })
    js_payload = "const CROPS = " + json.dumps(
        data, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    start = prior_js.index("const CROPS = [")
    end = prior_js.index("];", start) + 3
    js = prior_js[:start] + js_payload + prior_js[end:]
    # UI logic must run after normal market/unit initialization.
    js = replace_once(
        js,
        "fillSelect($('crop'), CROPS, prefs.crop_id || CROPS[0].id);",
        "// Grouped catalog initialization runs after markets and units.",
    )
    js = replace_once(
        js,
        "fillSelect($('prevUnit'), INPUT_UNITS, $('priceUnit').value);",
        "fillSelect($('prevUnit'), INPUT_UNITS, $('priceUnit').value);\n"
        "  setupCropCatalog();",
    )
    js = replace_once(
        js,
        "/* ---------- 表單初始化 ---------- */",
        JS_CATALOG_CONTROLS + "\n/* ---------- 表單初始化 ---------- */",
    )
    # Reject invalid empty dropdown before calling browser forecast.
    js = replace_once(
        js,
        "if (!cropId) errors.push('請選擇品項');",
        "if (!cropId) errors.push('請選擇有有效公開行情的品項');",
    )
    js = replace_once(
        js,
        "if (!marketId) errors.push('請選擇參考市場');",
        "if (!marketId) errors.push('請選擇參考市場');\n"
        "  const candidate = findSelectedCrop();\n"
        "  if (candidate && !(candidate.markets[marketId]?.observations > 0)) "
        "errors.push('該市場此品項沒有公開行情，請換市場');",
    )
    html = replace_once(
        prior_html,
        "透過安全 HTTPS 登入，輸入店價即可取得 7／14 天 A／B 推估；不依賴語言模型",
        "不需帳號密碼，支援 61 個官方市場品項（蔬菜、水果、魚肉蛋）；7／14 天來源與估計方法會明確標示。",
    )
    # Preserve the owner-approved public-facing name on future site rebuilds.
    # This does not rename the TW01 source project or touch original Windows UI.
    html = replace_once(
        html, "<title>現場菜價預測（7／14 天）</title>",
        "<title>菜市場現場價格預測</title>",
    )
    html = replace_once(
        html, "<h1>現場菜價預測</h1>",
        "<h1>菜市場現場價格預測</h1>",
    )
    html = replace_once(
        html,
        'content="現場菜價 7／14 天預測（TW01，臺中公開市場行情參考）"',
        'content="菜市場現場價格預測（7／14 天，臺中公開市場行情參考）"',
    )
    html = replace_once(
        html,
        '<label for="crop">品項</label>\n          <select id="crop" name="crop_id" required></select>',
        '<label for="crop">品項（可搜尋並按類別篩選）</label>\n'
        '          <div class="catalog-tools">\n'
        '            <select id="cropCategory" aria-label="品項分類"></select>\n'
        '            <input id="cropSearch" type="search" placeholder="搜尋例如：大白菜、蘿蔔、番茄、雞蛋" autocomplete="off" aria-label="搜尋品項">\n'
        '          </div>\n'
        '          <select id="crop" name="crop_id" required></select>\n'
        '          <p id="cropStatus" class="hint" aria-live="polite"></p>\n'
        '          <p id="cropMethodStatus" class="hint" aria-live="polite"></p>',
    )
    html = replace_once(
        html,
        '<p class="hint">用來對照公開市場行情，不會揭露你的店家。</p>',
        '<p class="hint">用來對照公開市場行情，不會揭露你的店家。</p>\n'
        '          <p id="marketPriceStatus" class="hint" aria-live="polite"></p>',
    )
    html = replace_once(
        html,
        "公開市場均價模型（臺中）；店價估計為現價錨定推估，未在同店驗證",
        "官方 61 個價格欄有 60 項曾有有效行情；牛心柿全部缺測。"
        "只有原三項使用凍結 RF/HGB，其他為未訓練歷史趨勢基準。全部皆非單店真值驗證。",
    )
    css = prior_css + """

/* Grouped public-market catalog controls; original Windows site untouched. */
.catalog-tools { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 12px; }
.catalog-tools select { flex: 1 1 140px; max-width: 100%; }
.catalog-tools input { flex: 2 1 180px; min-width: 110px; max-width: 100%; }
#crop { width: 100%; }
#cropStatus, #cropMethodStatus, #marketPriceStatus { margin: 5px 0; }
#cropMethodStatus { font-weight: 600; }
"""
    output.mkdir(parents=True)
    for name, value in {
        "index.html": html, "app.js": js, "style.css": css,
    }.items():
        (output / name).write_text(value, encoding="utf-8")
    (output / "catalog.json").write_bytes(catalog_path.read_bytes())
    return {
        "public_items": 61, "price_available": 60,
        "frozen_models": 3, "baseline_only": 57,
        "file_sizes": {p.name: p.stat().st_size for p in output.iterdir()},
        "original_windows_web_modified": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(args.catalog, args.output), ensure_ascii=False, indent=2))

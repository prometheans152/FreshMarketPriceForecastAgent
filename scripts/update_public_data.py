"""公開行情手動更新流程（T30；2026-10-04 第二輪審查後重構，修 F04／F05）。

流程：取得最新 JSON（下載或 --input 本地檔）→ 驗證（HTTP 狀態／SHA256／加強版
schema）→ 與 data/raw/ 最新快照比較（新增觀測日數）→ 存新快照（帶日期、永不
覆蓋舊檔）→（選配）--refresh-release-history 把「release 截止日之後的新日期」
追加到模型包的 public_history.parquet（推論特徵來源）→（選配）--reload-check
以全新 ForecastEngine 重載並印出 public_cutoff，證明重啟後讀到新日期。

F04 修正：非 dry-run 下載路徑把 candidate 搬進快照目錄後，後續刷新一律使用
「已保存的路徑變數」（saved），不再回讀已不存在的原始 candidate 路徑；全程
try/except 受控，任何失敗都寫報告 JSON、回非零退出碼，並保留已完成的合法
部分（快照已保存就保留，並在報告說明 release 歷史未刷新）。

F05a 修正：parquet 更新改為「備份 → 寫入同目錄暫存檔 → 逐列核對（列數＝舊＋
新、舊列逐列相同、新區段全為預期新日期與內容）→ os.replace 原子替換 → 替換
後再驗證可讀」；任一步失敗即確認目標仍是舊內容（不是就自動從備份還原並驗證）。

F05b 修正：schema 驗證加強——每列必要欄位存在（市場名稱／訪價日期＋三個支援
品項欄：甘藍（平地高麗菜）／青江白菜／絲瓜）、日期可解析 YYYYMMDD、三品項欄
值可轉 float 且有限（None／空字串／NaN＝缺測允許；0＝無價依契約轉缺測；
Infinity／負值／無法解析拒絕）、(市場, 日期) 鍵唯一；壞 JSON 回受控 schema
錯誤，不噴 traceback。

F05c：--reload-check 以全新 ForecastEngine 證明「重啟／重建引擎」後讀到新
public_cutoff。注意：已啟動中的引擎／API 服務不會自動看到新行情，必須重啟
服務或重建引擎（明確步驟見 docs/OPERATIONS.md §6）。

F05d：報告以 date_semantics 區分三個概念——「快照截止日」（全域最大觀測日）、
「特徵實際可見日」（預測特徵經 visible_delay_days 回看後實際用到的最新價格
日，因市場／品項而異，由推論端計算）、「資料版本」（manifest 的訓練快照
SHA256／observation_end，不隨刷新改變）。

R07 修正（第三輪獨立審查，2026-10-04）——更新失敗的狀態契約：
1. --config 載入移入受控區：設定檔不存在／壞 YAML／編碼錯時不再裸拋
   FileNotFoundError／YAMLError，而是寫報告 JSON（status=failed、
   failure_stage=config、error 以 config_error 開頭）後回 exit 1。
2. 明確提交／回復邊界：快照保存與 release 歷史原子替換（逐列核對通過）即視為
   「已提交」。reload-check 失敗時不回滾已提交的新資料（回滾反而讓磁碟內容與
   已核對的成功更新不一致），改回獨立狀態 status="data_updated_reload_failed"
   （exit 5，reloaded=False 的成功資料更新），報告附手動重啟服務指引與備份位置；
   本 run 未落地任何資料（dry-run／無新資料）時 reload-check 失敗仍為純驗證
   失敗（status=failed、exit 4）。

設計原則（design.md §8）：「行情刷新、模型發布、Qwen 載入是不同操作」。
本腳本只刷新公開行情（快照＋推論歷史 parquet），**完全不動**：
- 模型權重 model_h7.joblib／model_h14.joblib（重訓一律回 TRAIN_LOCAL 的 T08–T18）
- manifest.json／fixtures.json（記錄的是訓練當時的資料切分與 hash，不隨行情漂移）
- Qwen 或任何 SERVER 服務（載入與重啟是另一件事）

用法（專案根目錄，Git Bash；PYTHONPATH=src）：
  # 標準流程：從官方 URL 下載、驗證、比較、有新資料才存快照
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py

  # 只報告、不寫入任何檔案
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --dry-run

  # 用本地 JSON 代替下載（測試／離線核對用）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py \
      --input data/raw/taichung/retail_prices_20261003.json --dry-run

  # 下載並把新觀測日期追加到模型包推論歷史（原子替換＋自動備份／還原）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --refresh-release-history

  # 追加後另建引擎驗證重啟可讀到新 public_cutoff（建議與上一行同用）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py \
      --refresh-release-history --reload-check

  # 指定其他下載 URL（例：測試失效來源的錯誤處理）
  PYTHONPATH=src .venv/Scripts/python.exe scripts/update_public_data.py --url http://127.0.0.1:9/

離開代碼（與 configs/update_policy.yaml、docs/OPERATIONS.md 同步；R07 修復後
新增 5，各階段失敗行為不再以「失敗一律保留舊檔」概括，改以下表為準）：
  0＝成功（含「無新資料」）
  1＝參數／設定錯誤（含 --config 不存在／壞 YAML；報告記 failure_stage=config），
     或其他未預期但受控回報的失敗
  2＝schema 驗證失敗（含壞 JSON、缺欄、壞日期、Infinity／負值、重複鍵）
  3＝下載失敗（連線／HTTP／逾時）
  4＝寫入／核對失敗（歷史刷新的暫存寫入、逐列核對、原子替換、備份還原）；
     另含「本 run 未落地任何資料」時的 reload-check 失敗（純驗證失敗）
  5＝資料已更新但 reload-check 失敗（status=data_updated_reload_failed）：
     快照與 release 歷史已核對通過並落地（提交邊界），不回滾已提交的新資料；
     需手動重啟服務／重建引擎（docs/OPERATIONS.md §6）；舊資料已在備份
     （release_history.backup_path），確需回舊資料時可手動還原

各階段失敗行為（提交邊界＝快照保存＋release 歷史原子替換且逐列核對通過）：
  config：不寫入任何檔案，只寫報告 JSON（exit 1）
  download：舊檔全部保留（exit 3）
  schema：該檔不落地（exit 2）
  write：快照若已保存屬合法取得內容保留（partial_state 註明歷史未刷新）；
         release parquet 保護為舊內容、必要時自動從備份還原（exit 4）
  reload：本 run 有已提交資料 → 不回滾，status=data_updated_reload_failed、
          exit 5＋手動重啟指引（舊資料在備份）；本 run 無落地寫入（dry-run／
          無新資料）→ status=failed、exit 4（純驗證失敗）
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# 重用 T05 既有工具：下載、hash、不覆蓋命名、provenance（不重造，不改 src/）
from aiot_price.data.fetch_public import (
    analyze_snapshot,
    download_file,
    load_config,
    sha256_file,
    unique_path,
    write_provenance,
)
from aiot_price.data.load import KEY_DATE, KEY_MARKET, load_taichung_long
from aiot_price.data.schema import CROP_MAPPINGS

# 與 scripts/prepare_data.py 完全一致的排除規則：T06 品質決策，(停) 前綴市場排除
EXCLUDED_MARKET_PATTERN = "(停)"
# release 推論歷史 parquet 的固定欄位（package.py 產出）
HISTORY_COLUMNS = ["market_id", "date", "crop_id", "price"]
# 三個支援品項的來源欄位（F05b：欄位缺席＝schema 驗證失敗）
SUPPORTED_CROP_COLUMNS = [m.source_column for m in CROP_MAPPINGS.values()]

# 退出碼（與 configs/update_policy.yaml / docs/OPERATIONS.md 同步）
EXIT_OK = 0        # 成功（含無新資料）
EXIT_USAGE = 1     # 參數／設定錯誤（含 config 載入失敗）、未預期但受控回報的失敗
EXIT_SCHEMA = 2    # schema 驗證失敗（含壞 JSON）
EXIT_DOWNLOAD = 3  # 下載失敗
EXIT_WRITE = 4     # 寫入／核對失敗（含原子替換、備份還原）；無落地資料時的 reload-check 失敗
EXIT_RELOAD = 5    # R07：資料已更新但 reload-check 失敗（data_updated_reload_failed；不回滾已提交資料）


# ---------------------------------------------------------------------------
# schema 驗證（F05b 加強版）
# ---------------------------------------------------------------------------

def _price_cell_problem(value) -> str | None:
    """檢查支援品項價格欄的單一儲存格；回 None＝可接受，否則回問題描述。

    契約：None／空字串／NaN（含字串 "NaN"）＝缺測，允許；0＝該日無價格，
    下游 load_taichung_long 依契約轉缺測，允許；正有限數字允許。
    拒絕：Infinity／-Infinity（float() 會吃掉 "Infinity" 字串，必須擋）、
    負值（價格不可能為負）、無法轉 float 的內容。
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return f"無法轉為數字（{text!r}）"
    if math.isnan(number):
        return None  # NaN＝缺測
    if math.isinf(number):
        return f"非有限值（{text}）"
    if number < 0:
        return f"負值（{text}）"
    return None


def validate_schema(path: Path) -> tuple[dict, list[str]]:
    """加強版 schema 檢查（F05b）。

    檢查：JSON 可解析 → 頂層非空陣列 → 每列為物件 → 每列必要欄位存在
    （市場名稱／訪價日期＋三個支援品項欄）→ 日期可解析 YYYYMMDD → 三品項欄
    值可轉 float 且有限（缺測／0 依契約允許；Infinity／負值拒絕）→
    (市場, 日期) 鍵唯一。

    回傳 (stats, errors)：errors 非空＝驗證失敗，呼叫端不得用該檔做任何更新。
    """
    errors: list[str] = []
    # 壞 JSON（截斷／非 JSON／編碼錯）一律回受控 schema 錯誤，不噴 traceback
    try:
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return {}, [f"JSON 無法解析：{type(exc).__name__}: {exc}"]

    if not isinstance(rows, list):
        return {}, [f"頂層應為 JSON 陣列，實為 {type(rows).__name__}"]
    if len(rows) == 0:
        return {"row_count": 0}, ["列數為 0（空檔）"]

    non_dict = [i for i, r in enumerate(rows) if not isinstance(r, dict)]
    if non_dict:
        return {"row_count": len(rows)}, [
            f"第 {non_dict[0]} 列不是 JSON 物件（每列應為一個市場×日期的物件，"
            f"共 {len(non_dict)} 列）"
        ]

    # 每列必要欄位存在（值可為 None／空＝缺測，但欄位必須在）
    required = [KEY_MARKET, KEY_DATE] + SUPPORTED_CROP_COLUMNS
    missing_rows = [i for i, row in enumerate(rows) if any(k not in row for k in required)]
    if missing_rows:
        first = missing_rows[0]
        missing_here = [k for k in required if k not in rows[first]]
        errors.append(
            f"缺少必要欄位：{'、'.join(missing_here)}"
            f"（第 {first} 列起共 {len(missing_rows)} 列缺欄；"
            f"必要欄位＝{KEY_MARKET}、{KEY_DATE}＋支援品項欄{'、'.join(SUPPORTED_CROP_COLUMNS)}）"
        )

    bad_dates = 0
    bad_examples: list[str] = []
    for row in rows:
        d = str(row.get(KEY_DATE, ""))
        if not re.fullmatch(r"\d{8}", d):
            bad_dates += 1
            if len(bad_examples) < 3:
                bad_examples.append(d if d else "<空>")
        else:
            try:
                datetime.strptime(d, "%Y%m%d")
            except ValueError:
                bad_dates += 1
                if len(bad_examples) < 3:
                    bad_examples.append(f"{d}(無效日)")
    if bad_dates:
        errors.append(
            f"訪價日期格式錯誤 {bad_dates} 列（應為 YYYYMMDD，例：{bad_examples}）"
        )

    # 三品項欄值檢查：缺測／0 允許；Infinity／負值／無法解析拒絕
    bad_cells = 0
    cell_examples: list[str] = []
    for row in rows:
        for col in SUPPORTED_CROP_COLUMNS:
            problem = _price_cell_problem(row.get(col))
            if problem:
                bad_cells += 1
                if len(cell_examples) < 3:
                    cell_examples.append(f"{col}：{problem}")
    if bad_cells:
        errors.append(
            f"支援品項欄含不可用值 {bad_cells} 格（例：{'；'.join(cell_examples)}）；"
            f"僅接受 空值/NaN＝缺測、0＝無價（轉缺測）、正有限數字"
        )

    # (市場, 日期) 鍵唯一
    keys = [(str(r.get(KEY_MARKET, "")), str(r.get(KEY_DATE, ""))) for r in rows]
    n_dup = len(keys) - len(set(keys))
    if n_dup:
        errors.append(f"(市場名稱, 訪價日期) 鍵重複 {n_dup} 組（快照內每市場每日應只有一列）")

    stats = analyze_snapshot(path) if not errors else {"row_count": len(rows)}
    stats["row_count"] = len(rows)
    return stats, errors


# ---------------------------------------------------------------------------
# 快照比較
# ---------------------------------------------------------------------------

def find_latest_snapshot(out_dir: Path) -> tuple[Path | None, dict]:
    """找 out_dir 內內容日期最新的既有快照（retail_prices_*.json）當比較基準。

    以檔案內容的 max_date 為準（檔名日期只是下載日，不是觀測日）；
    同 max_date 時取 mtime 最新。沒有任何快照時回傳 (None, {})。
    """
    candidates = sorted(out_dir.glob("retail_prices_*.json"))
    best: Path | None = None
    best_key = ("", 0.0)
    for cand in candidates:
        try:
            stats = analyze_snapshot(cand)
        except (ValueError, json.JSONDecodeError, OSError):
            continue  # 壞檔不作為基準，也不刪除
        key = (stats["max_date"], cand.stat().st_mtime)
        if key > best_key:
            best, best_key = cand, key
    if best is None:
        return None, {}
    return best, {
        "path": str(best),
        "max_date": best_key[0],
        "sha256": sha256_file(best),
        "row_count": None,  # 由呼叫端視需要補
    }


def new_observation_dates(new_path: Path, baseline_dates: set[str]) -> list[str]:
    """回傳新檔有、基準沒有的觀測日期（YYYYMMDD 字串，排序）。"""
    with open(new_path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return sorted({str(r.get(KEY_DATE, "")) for r in rows} - baseline_dates)


def baseline_date_set(baseline: Path) -> set[str]:
    with open(baseline, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {str(r.get(KEY_DATE, "")) for r in rows}


# ---------------------------------------------------------------------------
# release 推論歷史刷新（--refresh-release-history；F05a 原子替換版）
# ---------------------------------------------------------------------------

def build_release_rows(json_path: Path) -> pd.DataFrame:
    """把新 JSON 轉成與 public_history.parquet 同結構的長表。

    與訓練前處理（prepare_data.py／package.py）一致：
    - 只取 CROP_MAPPINGS 三品項欄位（crop_raw → crop_id）
    - 0／負值／解析失敗 → NaN（load_taichung_long 已處理；schema 閘門已先擋負值）
    - 排除 (停) 前綴市場
    """
    crop_cols = [m.source_column for m in CROP_MAPPINGS.values()]
    long_df, _report = load_taichung_long(json_path, crop_columns=crop_cols)
    keep = ~long_df["market_id"].str.contains(EXCLUDED_MARKET_PATTERN, regex=False)
    df = long_df[keep].copy()
    df["crop_id"] = df["crop_raw"].map(
        {m.source_column: cid for cid, m in CROP_MAPPINGS.items()}
    )
    return df[HISTORY_COLUMNS]


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    """寫 parquet 的薄包裝。獨立成函式是為了讓故障注入測試可以 monkeypatch
    這裡模擬「寫入中斷」或「寫出錯誤內容」，正式路徑行為不變。"""
    df.to_parquet(path, index=False)


def _atomic_replace(src: Path, dst: Path) -> None:
    """os.replace 原子替換的薄包裝（同上，供故障注入測試 monkeypatch）。"""
    os.replace(src, dst)


def _verify_history_file(path: Path, expected_old: pd.DataFrame,
                         appended: pd.DataFrame) -> tuple[bool, str]:
    """逐列核對候選檔（暫存檔或已替換的目標）。

    核對：可讀 → 列數＝舊＋新 → 舊區段逐列與更新前完全相同 → 新區段逐列與
    預期追加內容相同（日期當然全部是預期的新日期）。回 (ok, note)。
    """
    try:
        got = pd.read_parquet(path)
    except Exception as exc:  # pyarrow 各種損毀錯誤統一受控
        return False, f"無法讀取 {path.name}：{type(exc).__name__}: {exc}"
    expected_total = len(expected_old) + len(appended)
    if len(got) != expected_total:
        return False, f"列數不符：預期 {len(expected_old)}(舊)+{len(appended)}(新)={expected_total}，實為 {len(got)}"
    old_part = got.iloc[: len(expected_old)].reset_index(drop=True)
    if not old_part.equals(expected_old.reset_index(drop=True)):
        return False, "舊列內容不一致（應一列不改）"
    new_part = got.iloc[len(expected_old):].reset_index(drop=True)
    if not new_part.equals(appended.reset_index(drop=True)):
        return False, "新列內容與預期追加內容不一致"
    return True, "逐列核對通過（列數＝舊＋新、舊列相同、新列為預期日期與內容）"


def _restore_from_backup(backup: Path, hist_path: Path,
                         expected: pd.DataFrame) -> tuple[bool, str]:
    """從備份還原 hist_path 並驗證還原結果＝更新前內容。"""
    try:
        shutil.copyfile(backup, hist_path)
    except OSError as exc:
        return False, f"備份複製回目標失敗：{type(exc).__name__}: {exc}（請手動以 {backup} 還原）"
    try:
        got = pd.read_parquet(hist_path)
    except Exception as exc:
        return False, f"還原後仍無法讀取目標：{type(exc).__name__}: {exc}（請手動以 {backup} 還原）"
    if not got.reset_index(drop=True).equals(expected.reset_index(drop=True)):
        return False, "還原後內容與更新前不一致（請手動以備份還原）"
    return True, f"已自動從備份還原並驗證（{backup.name}）"


def _ensure_target_is_old(hist_path: Path, backup: Path,
                          history: pd.DataFrame) -> tuple[bool, str, bool]:
    """確認目標 parquet 目前就是更新前內容；不是才從備份還原。

    回 (ok, note, restored)：restored=True 表示實際執行了備份還原。
    """
    try:
        got = pd.read_parquet(hist_path)
    except Exception:
        got = None
    if got is not None and len(got) == len(history) and \
            got.reset_index(drop=True).equals(history.reset_index(drop=True)):
        return True, "目標從未被更動（仍是完整可讀的舊檔）", False
    ok, note = _restore_from_backup(backup, hist_path, history)
    return ok, note, ok


def refresh_release_history(
    json_path: Path,
    release_dir: Path,
    dry_run: bool,
) -> dict:
    """把 release 截止日之後的新日期列「只追加」到 public_history.parquet。

    F05a 原子替換版，保證：
    - 先備份（public_history.backup_YYYYMMDD_HHMMSS.parquet）
    - 新內容寫進同目錄暫存檔，逐列核對通過後才 os.replace 原子替換目標
    - 替換後再驗證可讀；任一步失敗即確保目標回到舊內容（必要時自動還原備份）
    - 舊列一列不改；新列 (市場,品項,日期) 鍵已存在於 release 則略過（防重複）
    - 模型權重／manifest／fixtures 完全不讀寫
    """
    result: dict = {"release_dir": str(release_dir), "dry_run": dry_run}
    hist_path = release_dir / "public_history.parquet"
    if not hist_path.exists():
        result.update({"ok": False, "changed": False,
                       "error": f"找不到 {hist_path}"})
        return result

    try:
        history = pd.read_parquet(hist_path)
    except Exception as exc:
        result.update({"ok": False, "changed": False,
                       "error": f"既有 public_history.parquet 無法讀取：{type(exc).__name__}: {exc}"})
        return result
    missing_cols = [c for c in HISTORY_COLUMNS if c not in history.columns]
    if missing_cols:
        result.update({"ok": False, "changed": False,
                       "error": f"release 歷史缺欄位：{missing_cols}"})
        return result

    history = history.reset_index(drop=True)
    cutoff = history["date"].max()
    result["release_cutoff_date"] = pd.Timestamp(cutoff).strftime("%Y-%m-%d")

    # manifest 只讀取對照用（observation_end 是訓練當時的快照截止，不隨刷新改）
    manifest_path = release_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
        result["manifest_observation_end"] = manifest.get("source", {}).get("observation_end")
        result["manifest_note"] = "manifest 記錄訓練快照截止日（資料版本），行情刷新不修改 manifest"

    new_df = build_release_rows(json_path)
    beyond = new_df[new_df["date"] > cutoff]
    new_dates = sorted({pd.Timestamp(d).strftime("%Y-%m-%d") for d in beyond["date"]})

    result.update({
        "history_rows_before": int(len(history)),
        "new_dates_beyond_cutoff": new_dates,
        "n_new_dates": len(new_dates),
    })

    if beyond.empty:
        result.update({"ok": True, "changed": False,
                       "reason": "release 截止日之後沒有新觀測日期，不修改任何檔案",
                       "last_date_after_refresh": result["release_cutoff_date"]})
        return result

    # 防重複：排除 release 已存在的 (市場,品項,日期) 鍵
    existing_keys = set(
        zip(history["market_id"], history["crop_id"],
            pd.DatetimeIndex(history["date"]).strftime("%Y-%m-%d"))
    )
    beyond = beyond.copy()
    beyond["_key"] = list(zip(
        beyond["market_id"], beyond["crop_id"],
        pd.DatetimeIndex(beyond["date"]).strftime("%Y-%m-%d"),
    ))
    n_dup = int(beyond["_key"].isin(existing_keys).sum())
    beyond = beyond[~beyond["_key"].isin(existing_keys)]
    beyond = beyond.drop(columns="_key")
    result["n_duplicate_keys_skipped"] = n_dup

    append = beyond.sort_values(["date", "market_id", "crop_id"])[HISTORY_COLUMNS].reset_index(drop=True)
    result["rows_to_append"] = int(len(append))
    result["appended_markets"] = sorted(append["market_id"].unique().tolist())
    result["appended_crops"] = sorted(append["crop_id"].unique().tolist())

    if dry_run:
        result.update({"ok": True, "changed": False, "dry_run_note": "僅報告，未寫入"})
        return result

    # ---- F05a：備份 → 暫存寫入 → 逐列核對 → 原子替換 → 替換後驗證 → 失敗自動還原 ----
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = release_dir / f"public_history.backup_{stamp}.parquet"
    tmp_path = release_dir / f".public_history.tmp_{stamp}.parquet"
    result["backup_path"] = str(backup)
    result["temp_path"] = str(tmp_path)

    try:
        shutil.copyfile(hist_path, backup)
    except OSError as exc:
        result.update({"ok": False, "changed": False,
                       "error": f"備份失敗，未動原檔：{type(exc).__name__}: {exc}"})
        return result

    combined = pd.concat([history, append], ignore_index=True)

    def _abort(error: str) -> dict:
        """任一寫入步驟失敗的共通收尾：確保目標是舊內容、清暫存檔、回失敗結果。"""
        ok_target, note, restored = _ensure_target_is_old(hist_path, backup, history)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass  # 暫存檔清不掉不影響目標正確性；保留供人工檢查
        result.update({
            "ok": False, "changed": False, "error": error,
            "target_is_old_content": bool(ok_target),
            "target_state_note": note,
            "restored_from_backup": bool(restored),
        })
        return result

    try:
        _write_parquet(combined, tmp_path)
    except Exception as exc:  # 寫入中斷（磁碟滿／注入失敗等）
        return _abort(f"暫存檔寫入失敗：{type(exc).__name__}: {exc}")

    ok_verify, verify_note = _verify_history_file(tmp_path, history, append)
    if not ok_verify:
        return _abort(f"暫存檔逐列核對失敗：{verify_note}")

    try:
        _atomic_replace(tmp_path, hist_path)
    except Exception as exc:  # 替換前中斷
        return _abort(f"原子替換失敗：{type(exc).__name__}: {exc}")

    ok_after, after_note = _verify_history_file(hist_path, history, append)
    if not ok_after:
        return _abort(f"替換後驗證失敗：{after_note}")

    result.update({
        "ok": True,
        "changed": True,
        "history_rows_after": int(len(combined)),
        "old_rows_unchanged": True,
        "written_dates": sorted({pd.Timestamp(d).strftime("%Y-%m-%d") for d in append["date"]}),
        "last_date_after_refresh": pd.Timestamp(combined["date"].max()).strftime("%Y-%m-%d"),
        "post_replace_verified": after_note,
    })
    return result


# ---------------------------------------------------------------------------
# reload-check（F05c）
# ---------------------------------------------------------------------------

def engine_public_cutoff(release_dir: Path) -> tuple[str | None, str | None]:
    """建立「全新」ForecastEngine 並回傳其 public_cutoff（YYYY-MM-DD 字串）。

    回 (cutoff, error)：模擬服務重啟／引擎重建後實際讀到的行情截止日。
    注意 src/ 不因本腳本修改；這裡只消費 ForecastEngine（PYTHONPATH=src）。
    """
    try:
        from aiot_price.models.predict import ForecastEngine  # 延遲 import：不用本功能就不載模型
        engine = ForecastEngine(release_dir)
        return str(engine.public_cutoff.date()), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="公開行情手動更新：下載→驗證→與最新快照比較→（選配）刷新模型包推論歷史→（選配）重載檢查",
    )
    parser.add_argument("--config", default="configs/data_sources.yaml", help="來源設定 YAML")
    parser.add_argument("--source", default=None, help="設定檔中的來源鍵；預設第一個採用中來源")
    parser.add_argument("--url", default=None, help="覆蓋下載 URL（測試失效來源用）")
    parser.add_argument("--input", default=None, help="以本地 JSON 檔代替下載（測試用；與 --url 互斥）")
    parser.add_argument("--out-dir", default="data/raw/taichung", help="快照與 provenance 目錄")
    parser.add_argument("--release-dir", default="models/releases/0.1.0", help="要刷新推論歷史的模型包目錄")
    parser.add_argument("--refresh-release-history", action="store_true",
                        help="把 release 截止日之後的新日期追加到 public_history.parquet（模型權重不動）")
    parser.add_argument("--reload-check", action="store_true",
                        help="刷新前後各建立一個全新 ForecastEngine 並印出 public_cutoff，"
                             "證明重啟／重建引擎後讀到新日期（已啟動中的服務不會自動看到新行情）")
    parser.add_argument("--dry-run", action="store_true", help="只報告，不寫入任何檔案")
    parser.add_argument("--timeout", type=float, default=120.0, help="下載逾時秒數")
    parser.add_argument("--report", default=None, help="把完整報告寫成 JSON（例：outputs/update_tests/x.json）")
    args = parser.parse_args(argv)

    if args.input and args.url:
        print("錯誤：--input 與 --url 互斥（本地檔不需要下載 URL）", file=sys.stderr)
        return EXIT_USAGE

    report: dict = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "script": "scripts/update_public_data.py",
        "argv": vars(args),
        "mode": {"dry_run": bool(args.dry_run),
                 "refresh_release_history": bool(args.refresh_release_history),
                 "reload_check": bool(args.reload_check)},
        "status": None,
        "error": None,
    }

    # ---- 第 0 步：決定下載 URL（--url > 設定檔採用中來源） ----
    url = args.url
    source_cfg: dict = {}
    if not args.input:
        # R07：--config 載入移入受控區——不存在／壞 YAML／編碼錯時不再裸拋例外，
        # 而是產生報告 JSON（status=failed、failure_stage=config、error 以
        # config_error 開頭）後回 exit 1，指定的 --report 一定會生成。
        try:
            config = load_config(args.config)
        except Exception as exc:  # FileNotFoundError／yaml.YAMLError／UnicodeDecodeError／OSError
            report.update({"status": "failed",
                           "failure_stage": "config",
                           "error": f"config_error：設定檔載入失敗（{args.config}）："
                                    f"{type(exc).__name__}: {exc}",
                           "old_files_kept": True})
            _emit(report, args)
            print(f"錯誤：config_error：設定檔載入失敗（{args.config}）："
                  f"{type(exc).__name__}: {exc}；未寫入任何檔案。", file=sys.stderr)
            return EXIT_USAGE
        sources = (config or {}).get("sources") or {}
        if args.source:
            source_cfg = sources.get(args.source) or {}
        else:
            adopted = [(k, v) for k, v in sources.items()
                       if isinstance(v, dict) and v.get("adopted")]
            if adopted:
                args.source, source_cfg = adopted[0]
        if url is None:
            url = source_cfg.get("download_url")
        if not url:
            report.update({"status": "failed",
                           "failure_stage": "config",
                           "error": "無法決定下載 URL（--url 未給、設定檔無採用中來源）"})
            _emit(report, args)
            return EXIT_USAGE
    report["source"] = {"type": "local_file" if args.input else "download",
                        "url": url, "source_key": args.source or None,
                        "input_path": args.input}

    # ---- 第 1 步：取得 JSON（下載到系統暫存，驗證通過且非 dry-run 才落盤） ----
    tmp_dir = Path(tempfile.mkdtemp(prefix="aiot_update_"))
    candidate = Path(args.input) if args.input else tmp_dir / "candidate.json"
    if args.input:
        if not candidate.exists():
            report.update({"status": "failed", "error": f"--input 檔不存在：{candidate}"})
            _emit(report, args)
            return EXIT_USAGE
        report["sha256"] = sha256_file(candidate)
    else:
        try:
            info = download_file(url, candidate, timeout=args.timeout)
            report["download"] = info
            report["sha256"] = sha256_file(candidate)
            print(f"下載：HTTP {info['http_status']}｜{info['bytes']} bytes｜{info['duration_seconds']}s")
            print(f"SHA256：{report['sha256']}")
        except Exception as exc:  # URLError／HTTPError／timeout／OSError 統一處理，不崩潰
            report.update({"status": "failed",
                           "error": f"下載失敗：{url} → {type(exc).__name__}: {exc}",
                           "old_files_kept": True})
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _emit(report, args)
            print(f"錯誤：下載失敗（{type(exc).__name__}: {exc}）；舊檔全部保留，未寫入任何資料。",
                  file=sys.stderr)
            return EXIT_DOWNLOAD

    saved: Path | None = None  # F04：快照保存後的「已保存路徑」，後續一律用它
    try:
        # ---- 第 2 步：schema 驗證（F05b 加強版） ----
        stats, schema_errors = validate_schema(candidate)
        report["schema_check"] = {"ok": not schema_errors, "errors": schema_errors, "stats": stats}
        if schema_errors:
            report.update({"status": "failed",
                           "error": "schema 驗證失敗：" + "；".join(schema_errors),
                           "old_files_kept": True})
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _emit(report, args)
            print(f"錯誤：schema 驗證失敗，不採用此檔；" + "；".join(schema_errors), file=sys.stderr)
            return EXIT_SCHEMA
        print(f"schema 檢查通過：列數 {stats['row_count']}｜欄位 {stats['field_count']}｜"
              f"日期 {stats['min_date']}~{stats['max_date']}（{stats['date_count']} 日）｜市場 {stats['market_count']}")

        # ---- 第 3 步：與現有最新快照比較 ----
        out_dir = Path(args.out_dir)
        baseline, base_meta = find_latest_snapshot(out_dir)
        if baseline is None:
            report["snapshot_comparison"] = {"baseline": None,
                                             "note": "out-dir 沒有既有快照，本次全部日期均視為新取得"}
            new_dates = sorted({str(r.get(KEY_DATE, "")) for r in json.load(open(candidate, encoding="utf-8"))})
        else:
            base_dates = baseline_date_set(baseline)
            new_dates = new_observation_dates(candidate, base_dates)
            same_hash = report["sha256"] == base_meta["sha256"]
            report["snapshot_comparison"] = {
                "baseline": base_meta["path"],
                "baseline_max_date": base_meta["max_date"],
                "baseline_sha256": base_meta["sha256"],
                "same_hash_as_baseline": same_hash,
                "new_dates": new_dates,
                "n_new_dates": len(new_dates),
            }
            print(f"比較基準：{baseline.name}（觀測至 {base_meta['max_date']}，SHA256 {'相同' if same_hash else '不同'}）")
            print(f"新增觀測日期：{len(new_dates)} 日{(' ' + '、'.join(new_dates)) if new_dates else ''}")

        has_new = len(new_dates) > 0
        report["has_new_data"] = has_new

        # ---- reload-check（刷新前）：先記錄目前引擎讀到的截止日 ----
        reload_before: str | None = None
        reload_error: str | None = None
        if args.reload_check:
            reload_before, reload_error = engine_public_cutoff(Path(args.release_dir))
            if reload_error is None:
                print(f"reload-check：刷新前引擎 public_cutoff = {reload_before}")
            else:
                print(f"reload-check：刷新前引擎建立失敗：{reload_error}", file=sys.stderr)

        # ---- 第 4 步：存快照（僅非 dry-run 且有新資料；hash 相同＝無新資料不動） ----
        provenance = None
        if not args.dry_run and has_new:
            stamp = datetime.now().strftime("%Y%m%d")
            out_dir.mkdir(parents=True, exist_ok=True)
            dest = unique_path(out_dir / f"retail_prices_{stamp}.json")
            if args.input:
                shutil.copyfile(candidate, dest)
            else:
                shutil.move(str(candidate), str(dest))
            saved = dest  # F04：candidate 在 download 模式已不存在，之後一律用 saved
            report["snapshot_saved"] = str(dest)
            if not args.input and source_cfg:
                provenance = write_provenance(out_dir, dest, source_cfg,
                                              report.get("download", {}), stats)
                report["provenance"] = str(provenance)
            print(f"新快照已存：{dest}" + (f"｜provenance：{provenance}" if provenance else ""))
        else:
            reason = "dry-run" if args.dry_run else ("無新資料（hash/日期與既有快照相同），依策略不另存檔" if not has_new else "")
            report["snapshot_saved"] = None
            report["snapshot_not_saved_reason"] = reason
            if reason:
                print(f"快照未存：{reason}")

        # ---- 第 5 步：（選配）刷新 release 推論歷史（F04：用已保存路徑） ----
        refresh_json_source = saved if saved is not None else candidate
        if args.refresh_release_history:
            try:
                refresh = refresh_release_history(refresh_json_source, Path(args.release_dir),
                                                  dry_run=args.dry_run)
            except Exception as exc:  # 任何未預期例外也走同一受控失敗路徑
                refresh = {"ok": False, "changed": False,
                           "error": f"未預期失敗：{type(exc).__name__}: {exc}"}
            report["release_history"] = refresh
            if not refresh.get("ok", False):
                report.update({"status": "failed",
                               "error": f"release 歷史刷新失敗：{refresh.get('error')}"})
                if saved is not None:
                    report["partial_state"] = {
                        "snapshot_saved": str(saved),
                        "note": "快照已保存（合法部分，保留不回滾）；release 歷史未刷新，"
                                "目標 parquet 已保護為舊內容（見 release_history.target_state_note）",
                    }
                _emit(report, args)
                print(f"錯誤：release 歷史刷新失敗：{refresh.get('error')}", file=sys.stderr)
                return EXIT_WRITE
            rh = refresh
            if rh.get("changed"):
                print(f"release 歷史已更新（原子替換）：{rh['history_rows_before']} → {rh['history_rows_after']} 列"
                      f"（追加 {rh['rows_to_append']} 列、新日期 {rh['n_new_dates']} 日、備份 {rh['backup_path']}｜{rh['post_replace_verified']}）")
            else:
                print(f"release 歷史未變更：{rh.get('reason') or rh.get('dry_run_note')}")

        # ---- 第 6 步：（選配）reload-check（刷新後）：證明重建引擎讀到新日期 ----
        # R07 提交邊界：快照已保存或 release 歷史已原子替換（逐列核對通過）＝已提交；
        # 此後 reload-check 失敗不回滾已提交的新資料（回滾反而讓磁碟內容與已核對的
        # 成功更新不一致），改回獨立狀態 data_updated_reload_failed（exit 5）並附
        # 手動重啟指引。本 run 未落地任何資料（dry-run／無新資料）時則仍是純驗證
        # 失敗（status=failed、exit 4）。
        reload_failed_msg: str | None = None
        if args.reload_check:
            reload_after, reload_error_after = engine_public_cutoff(Path(args.release_dir))
            if reload_error is not None or reload_error_after is not None:
                msg = reload_error or reload_error_after
                data_committed = (saved is not None) or bool(
                    (report.get("release_history") or {}).get("changed"))
                if not data_committed:
                    report["reload_check"] = {"ok": False, "error": msg,
                                              "cutoff_before": reload_before,
                                              "cutoff_after": reload_after,
                                              "release_dir": str(Path(args.release_dir)),
                                              "data_committed": False}
                    report.update({"status": "failed",
                                   "error": f"reload-check 失敗（本 run 未寫入任何資料，屬純驗證失敗）：{msg}"})
                    _emit(report, args)
                    print(f"錯誤：reload-check 失敗：{msg}", file=sys.stderr)
                    return EXIT_WRITE
                rh = report.get("release_history") or {}
                backup_note = rh.get("backup_path")
                report["reload_check"] = {
                    "ok": False,
                    "error": msg,
                    "cutoff_before": reload_before,
                    "cutoff_after": reload_after,
                    "release_dir": str(Path(args.release_dir)),
                    "data_committed": True,
                    "reloaded": False,
                    "status_meaning": "資料已更新（快照／release 歷史已核對通過並落地）、"
                                      "服務重載驗證失敗（reloaded=False）——不回滾已提交的新資料；"
                                      "需手動重啟服務或重建引擎",
                    "manual_restart_required": True,
                    "restart_guidance": "資料已更新、服務重載失敗——需手動重啟服務：依 "
                                        "docs/OPERATIONS.md §6 重啟推論服務（本機 API＝重啟 "
                                        "Uvicorn 行程；SERVER 部署後＝重啟推論服務行程），"
                                        "重啟後重跑 --reload-check 確認 public_cutoff 已是新日期；"
                                        "確需回到舊資料時，以報告 release_history.backup_path 的備份（"
                                        + (str(backup_note) if backup_note else "見 release_history.backup_path")
                                        + "）手動覆蓋回 public_history.parquet。",
                }
                reload_failed_msg = msg
                print(f"警告：reload-check 失敗：{msg}；資料已更新不回滾"
                      f"（status=data_updated_reload_failed，exit 5），需手動重啟服務"
                      f"（docs/OPERATIONS.md §6）；舊資料已在備份。", file=sys.stderr)
            else:
                changed = reload_before != reload_after
                report["reload_check"] = {
                    "ok": True,
                    "release_dir": str(Path(args.release_dir)),
                    "cutoff_before": reload_before,
                    "cutoff_after": reload_after,
                    "changed": bool(changed),
                    "note": "以兩個全新 ForecastEngine 例證明重啟／重建引擎後讀到的新截止日；"
                            "已啟動中的引擎／服務不會自動看到新行情，需重啟服務或重建引擎"
                            "（步驟見 docs/OPERATIONS.md §6）；模型權重未變。",
                }
                print(f"reload-check：刷新後引擎 public_cutoff = {reload_after}"
                      + (f"（已讀到新日期；權重未變）" if changed else "（與刷新前相同）"))

        # ---- F05d：報告中區分三個日期／版本概念 ----
        date_semantics: dict = {
            "snapshot_max_date": stats.get("max_date"),
            "snapshot_max_date_meaning": "快照截止日＝本次 JSON 的全域最大觀測日（跨所有市場／品項）",
            "feature_visible_note": "特徵實際可見日＝預測特徵經 visible_delay_days 回看後，該市場/品項實際"
                                    "用到的最新價格日，因市場／品項而異且可能早於快照截止日（由推論端計算，"
                                    "不等於快照截止日）",
            "data_version_meaning": "資料版本＝manifest 的訓練快照 SHA256／observation_end，"
                                    "行情刷新只延長 parquet，不改資料版本",
        }
        rh = report.get("release_history")
        if isinstance(rh, dict):
            date_semantics["release_history_last_date"] = rh.get(
                "last_date_after_refresh", rh.get("release_cutoff_date"))
            date_semantics["manifest_observation_end"] = rh.get("manifest_observation_end")
        else:
            manifest_path = Path(args.release_dir) / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as fh:
                        date_semantics["manifest_observation_end"] = \
                            json.load(fh).get("source", {}).get("observation_end")
                except (json.JSONDecodeError, OSError):
                    pass
        report["date_semantics"] = date_semantics

        # ---- 收尾 ----
        if reload_failed_msg is not None:
            # R07：資料已提交（快照／release 歷史核對通過並落地）、reload 驗證失敗——
            # 獨立狀態「reloaded=False 的成功資料更新」，不回滾、不算純失敗（exit 5）。
            report["status"] = "data_updated_reload_failed"
            report["error"] = (f"reload-check 失敗：{reload_failed_msg}；資料已更新不回滾，"
                               f"需手動重啟服務（docs/OPERATIONS.md §6），舊資料已在備份"
                               f"（release_history.backup_path）")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            _emit(report, args)
            print(f"狀態：{report['status']}（資料已更新；服務重載失敗，需手動重啟服務——docs/OPERATIONS.md §6）")
            return EXIT_RELOAD
        report["status"] = "ok" if has_new else "no_new_data"
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _emit(report, args)
        print(f"狀態：{report['status']}")
        return EXIT_OK

    except Exception as exc:  # 未預期例外：受控回報、寫報告、非零退出，不留半更新狀態
        report.update({"status": "failed",
                       "error": f"未預期失敗：{type(exc).__name__}: {exc}",
                       "traceback_tail": traceback.format_exc().strip().splitlines()[-3:]})
        if saved is not None:
            report["partial_state"] = {
                "snapshot_saved": str(saved),
                "note": "快照已保存（合法部分，保留不回滾）；其後步驟失敗，"
                        "release 歷史未刷新（目標 parquet 未被替換）",
            }
        else:
            report["old_files_kept"] = True
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _emit(report, args)
        print(f"錯誤：{report['error']}；舊檔保留（快照若已保存亦為合法取得內容）。", file=sys.stderr)
        return EXIT_WRITE


def _emit(report: dict, args) -> None:
    """把報告寫到 --report 指定路徑（沒指定就只印在 stdout）。"""
    if not args.report:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    print(f"報告 → {path}")


if __name__ == "__main__":
    sys.exit(main())

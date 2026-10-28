import { z } from "zod";

// D47 (2026-10-28): items mirror the Oracle public catalog the website forecasts
// (catalog.json; taichung_25 has never had a public price and is left out). The
// three original crops keep the frozen RF/HGB v0.1.0 model; the others use the
// 57-item pooled HGB through the Oracle /v1 full-catalog extension.
export const CROP_NAMES = Object.freeze({
  cabbage: "甘藍（平地高麗菜）", bok_choy: "青江白菜", sponge_gourd: "絲瓜", taichung_02: "花胡瓜", taichung_03: "結球白菜(山東白)",
  taichung_04: "蘿蔔", taichung_05: "胡蘿蔔", taichung_06: "青蔥", taichung_07: "胡瓜", taichung_09: "蕹菜(空心菜)",
  taichung_11: "香蕉(內銷)", taichung_12: "番石榴(珍珠)", taichung_13: "鳳梨(開英)", taichung_14: "荔枝(黑葉)",
  taichung_15: "火龍果(紅肉)", taichung_16: "芒果(愛文)", taichung_17: "木瓜", taichung_18: "文旦", taichung_19: "新世紀梨",
  taichung_20: "檸檬", taichung_21: "鳳梨(四號)", taichung_22: "火龍果(白肉)", taichung_23: "新興梨", taichung_24: "橫山梨",
  taichung_26: "甜柿", taichung_27: "紅柿(軟柿)", taichung_28: "桶柑", taichung_29: "椪柑", taichung_30: "海梨柑",
  taichung_31: "鳳梨(金鑽17號)", taichung_32: "柳橙", taichung_33: "蓮霧", taichung_34: "棗子", taichung_35: "茂谷柑",
  taichung_36: "芒果", taichung_37: "西瓜(大粒)", taichung_38: "小番茄_玉女", taichung_39: "小番茄_聖女", taichung_40: "花椰菜",
  taichung_41: "洋蔥(內銷)", taichung_42: "蒜頭", taichung_43: "吳郭魚", taichung_44: "虱目魚", taichung_45: "金目鱸",
  taichung_46: "龍虎斑", taichung_47: "午仔魚", taichung_48: "白蝦", taichung_49: "文蛤", taichung_50: "里肌肉",
  taichung_51: "後腿肉", taichung_52: "五花肉", taichung_53: "牛腱(冷凍牛肉)", taichung_54: "腿肉(冷凍牛肉)",
  taichung_55: "腩肉(冷凍牛肉)", taichung_56: "雞蛋", taichung_57: "鴨蛋", taichung_58: "肉雞", taichung_59: "土雞",
  taichung_60: "仿雞", taichung_61: "鴨子(土番鴨)",
});
export const CROPS = Object.freeze(Object.keys(CROP_NAMES));
export const MARKETS = Object.freeze([
  "中義市場", "南屯市場", "合作市場", "大甲第二市場", "東光市場", "梧棲第一市場",
  "沙鹿市場", "清水第一市場", "第三市場", "第二市場", "第五市場", "豐原第一市場", "霧峰市場",
]);
export const UNITS = Object.freeze(["NTD_per_taiwan_jin", "NTD_per_kg"]);
export const TOOL_NAMES = Object.freeze(["get_market_quote", "post_forecast"]);
export const TOOL_DESCRIPTIONS = Object.freeze({
  get_market_quote: "查詢臺中市 13 個公有零售市場、指定品項的公開市場均價與原始觀測日。這是政府公布的市場均價，不是今天的店價；資料截至 2026-10-02。品項只能用 crop_id 清單裡的代號，請對照中文名稱選擇；清單沒有的品項（例如金針菇、小白菜）要直接告訴使用者不支援，不可猜測或替換。",
  post_forecast: "用使用者今天在現場看到的店價，預測 7 天與 14 天後（精確日曆日）的漲跌方向與店價估計。呼叫前必須先向使用者問到：品項、市場、今天的價格與單位（元／台斤或元／公斤）；使用者沒給價格時要先詢問，不可用公開均價代替。只有 A 模式：不支援上週價（B）、保存或私人紀錄。結果未經同店到期驗證，模型測試誤差未勝不變價基準，回答時要一併說明。",
});
export const ANNOTATIONS = Object.freeze({
  readOnlyHint: true, destructiveHint: false, idempotentHint: false, openWorldHint: false,
});

const crop = z.enum(CROPS).describe(
  "品項代號（代號=中文名稱）：" + Object.entries(CROP_NAMES).map(([id, name]) => `${id}=${name}`).join("、"));
const market = z.enum(MARKETS).describe("臺中市公有零售市場，只能是這 13 個之一；已停用或不在清單的市場（例如建國市場）不支援。");
const price = z.number().finite().positive().max(1_000_000).describe("使用者今天在現場看到的價格（正數）。");
const unit = z.enum(UNITS).describe("價格單位：NTD_per_taiwan_jin＝元／台斤，NTD_per_kg＝元／公斤；一把、一顆、一盒等沒有重量的單位不可用。");
const observation = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe("看到價格的日期（臺北時間，YYYY-MM-DD）；省略時為今天。");
export const TOOL_INPUTS = Object.freeze({
  get_market_quote: z.strictObject({ crop_id: crop, market_id: market }),
  post_forecast: z.strictObject({
    crop_id: crop, market_id: market, current_price: price, price_unit: unit,
    observed_on: observation.optional(),
  }),
});
// Output is a bounded, validated, UNMODIFIED engine_result, plus provenance.
// Unlike an ML schema, this envelope may evolve without dropping engine data.
export const TOOL_OUTPUT = z.looseObject({
  tool: z.enum(TOOL_NAMES),
  input_echo: z.record(z.string(), z.unknown()),
  query_date: z.string(),
  engine_result: z.record(z.string(), z.unknown()),
  fact_text: z.string(),
  limits: z.array(z.string()),
  normalized_request: z.record(z.string(), z.unknown()).nullable().optional(),
  price_age_days_at_query: z.number().int().nullable().optional(),
});

export class ContractError extends Error {
  constructor(code, message) { super(message); this.name = "ContractError"; this.code = code; }
}

export function isValidDate(day) {
  if (typeof day !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return false;
  const parsed = Date.parse(`${day}T00:00:00Z`);
  return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 10) === day;
}

export function taipeiDay(now = new Date()) {
  // sv-SE emits YYYY-MM-DD and Asia/Taipei does not observe DST.
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Taipei", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(now);
}

export function offsetDay(ymd, number) {
  if (!isValidDate(ymd)) throw new ContractError("invalid_date", "觀測日無效。");
  const time = Date.parse(`${ymd}T00:00:00Z`) + number * 86400000;
  return new Date(time).toISOString().slice(0, 10);
}

export function validateArguments(name, value, now = new Date()) {
  if (!TOOL_NAMES.includes(name)) throw new ContractError("unknown_tool", "未知工具，本服務僅提供兩項工具。");
  if (value === null || Array.isArray(value) || typeof value !== "object")
    throw new ContractError("invalid_args", "工具參數必須為 JSON object。");
  if (Object.keys(value).length > 5)
    throw new ContractError("extra_fields", "參數欄位過多，B 模式或保存功能不支援。");
  const parsed = TOOL_INPUTS[name].safeParse(value);
  if (!parsed.success) throw new ContractError("invalid_args", "品項、市場、價格、單位或欄位不符合工具契約；禁止額外參數。");
  const clean = parsed.data;
  const today = taipeiDay(now);
  if (name === "post_forecast") {
    const observed = clean.observed_on ?? today;
    if (!isValidDate(observed) || observed > today)
      throw new ContractError("invalid_date", "觀測日必須是有效且不晚於臺北今日的 YYYY-MM-DD。");
    return { ...clean, observed_on: observed };
  }
  return clean;
}

export const LIMITS = Object.freeze([
  "公開市場均價不是任何店家的即時真實報價。",
  "匿名 A 為現場價錨定推估，未經同店到期驗證；公開模型測試未勝相應簡單基線。",
  "機率、信賴區間、因果解釋不可由 MCP 或語言模型自行推算。",
  "不支援 B 模式、保存、私人紀錄、任意 URL／檔案／程式。",
]);

const isRecord = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const goodNum = (v) => typeof v === "number" && Number.isFinite(v) && v > 0;

// Because the independent Oracle API V1 contract is not yet present, this
// verifier accepts the *existing frozen AgentTools response shape only*.
// If the owner of FORECASTENGINE_API_V1.md defines an envelope later, adapt
// this explicitly against the signed contract, not by guessing at deployment.
export function verifyEngineResult(name, args, raw) {
  if (!isRecord(raw)) throw new ContractError("bad_upstream", "ForecastEngine 回傳資料不是 JSON object。");
  if (name === "get_market_quote") {
    if (raw.ok !== true || raw.crop_id !== args.crop_id || raw.market_id !== args.market_id ||
        !goodNum(raw.price) || raw.unit !== "NTD_per_taiwan_jin" ||
        !isValidDate(raw.observed_date) || !isValidDate(raw.public_data_cutoff) ||
        raw.observed_date > raw.public_data_cutoff ||
        !Number.isInteger(raw.price_age_days_at_cutoff) || raw.price_age_days_at_cutoff < 0 ||
        offsetDay(raw.observed_date, raw.price_age_days_at_cutoff) !== raw.public_data_cutoff)
      throw new ContractError("insufficient_data", "沒有可驗證的公開行情，拒絕提供價格。");
  } else if (name === "post_forecast") {
    if (raw.error || raw.mode_executed !== "without_last_week" ||
        raw.store_id !== null || raw.crop_id !== args.crop_id || raw.market_id !== args.market_id ||
        !isValidDate(raw.public_data_cutoff) || typeof raw.model_version !== "string" ||
        !raw.model_version || typeof raw.data_version !== "string" || !raw.data_version ||
        !Array.isArray(raw.results) || raw.results.length !== 2 ||
        raw.results_with_last_week?.length)
      throw new ContractError("insufficient_data", "ForecastEngine 未提供可驗證的匿名 A 預測。");
    for (const [i, horizon] of [7, 14].entries()) {
      const item = raw.results[i];
      if (!isRecord(item) || item.horizon_days !== horizon ||
          !isValidDate(item.target_date) || item.target_date !== offsetDay(args.observed_on, horizon) ||
          !goodNum(item.price_estimate) || !Number.isFinite(item.relative_change_estimate) ||
          item.price_estimate_unit !== args.price_unit ||
          !["up", "down", "flat"].includes(item.direction) ||
          item.target_scope !== "store_price_estimate" || item.validation_scope !== "unvalidated" ||
          item.probability != null || item.interval_low != null || item.interval_high != null ||
          (item.warnings != null && (!Array.isArray(item.warnings) || !item.warnings.every(x => typeof x === "string"))))
        throw new ContractError("bad_upstream", "ForecastEngine 模式、日期、單位或結果契約不符；不得自行修正數字。");
    }
    if (raw.warnings != null && (!Array.isArray(raw.warnings) || !raw.warnings.every(x => typeof x === "string")))
      throw new ContractError("bad_upstream", "ForecastEngine warnings 格式不合法。");
  } else {
    throw new ContractError("unknown_tool", "未知工具。");
  }
  return raw; // Never rescale/round/recalculate or remove engine metadata.
}

// v1 API owner contract (docs/deployment/FORECASTENGINE_API_V1.md) returns
// a COMPLETE adapter envelope, not the bare AgentTools object. This verifier
// must preserve every upstream key including fact_text/limits/diagnostics.
export function verifyOracleEnvelope(name, args, payload) {
  if (!isRecord(payload) || payload.tool !== name || !isRecord(payload.input_echo) ||
      !isRecord(payload.engine_result) || !isValidDate(payload.query_date) ||
      !Array.isArray(payload.limits) || !payload.limits.every(x => typeof x === "string") ||
      typeof payload.fact_text !== "string" || !payload.fact_text.trim() ||
      !TOOL_OUTPUT.safeParse(payload).success)
    throw new ContractError("bad_upstream", "ForecastEngine HTTP v1 封套格式不完整。");
  if (Object.keys(payload.input_echo).length !== Object.keys(args).length ||
      Object.entries(args).some(([key, value]) => payload.input_echo[key] !== value))
    throw new ContractError("bad_upstream", "ForecastEngine input_echo 與實際工具參數不一致。");
  if (name === "get_market_quote") {
    if (payload.normalized_request !== null ||
        payload.price_age_days_at_query !==
        Math.round((Date.parse(payload.query_date + "T00:00:00Z") -
                    Date.parse(payload.engine_result.observed_date + "T00:00:00Z")) / 86400000))
      throw new ContractError("bad_upstream", "ForecastEngine 行情觀測日或查詢日不一致。");
  } else if (name === "post_forecast") {
    const normalized = payload.normalized_request;
    if (!isRecord(normalized) || normalized.crop_id !== args.crop_id ||
        normalized.market_id !== args.market_id ||
        normalized.current_price !== args.current_price ||
        normalized.price_unit !== args.price_unit ||
        normalized.observed_at !== args.observed_on + "T12:00:00+08:00" ||
        normalized.mode !== "without_last_week" || normalized.store_id !== null ||
        payload.engine_result.input_observed_at !== normalized.observed_at)
      throw new ContractError("bad_upstream", "ForecastEngine 的 A 模式標準化請求不一致。");
    if (payload.price_age_days_at_query !==
        Math.round((Date.parse(payload.query_date + "T00:00:00Z") -
                    Date.parse(payload.engine_result.public_data_cutoff + "T00:00:00Z")) / 86400000))
      throw new ContractError("bad_upstream", "ForecastEngine 預測資料年齡不一致。");
  }
  verifyEngineResult(name, args, payload.engine_result);
  return payload;
}

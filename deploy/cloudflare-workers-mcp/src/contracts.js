import { z } from "zod";

// This list mirrors the EXISTING Windows TW01 chatgpt_contracts.py; it is not
// permission to change the existing Python contract, market data, or model.
export const CROPS = Object.freeze(["cabbage", "bok_choy", "sponge_gourd"]);
export const MARKETS = Object.freeze([
  "中義市場", "南屯市場", "合作市場", "大甲第二市場", "東光市場", "梧棲第一市場",
  "沙鹿市場", "清水第一市場", "第三市場", "第二市場", "第五市場", "豐原第一市場", "霧峰市場",
]);
export const UNITS = Object.freeze(["NTD_per_taiwan_jin", "NTD_per_kg"]);
export const TOOL_NAMES = Object.freeze(["get_market_quote", "post_forecast"]);
export const TOOL_DESCRIPTIONS = Object.freeze({
  get_market_quote: "查詢指定臺中市場、指定品項的公開市場均價及原始觀測日。非即時單店報價；每次均以 ForecastEngine 最新可用結果為準。",
  post_forecast: "匿名 A 模式：以使用者指定的現場店價與實際觀測日向 ForecastEngine 查詢 t+7、t+14 日曆日預測。僅接受元／台斤或元／公斤，不支援 B、保存或私人紀錄；模型未完成真店驗證。",
});
export const ANNOTATIONS = Object.freeze({
  readOnlyHint: true, destructiveHint: false, idempotentHint: false, openWorldHint: false,
});

const crop = z.enum(CROPS);
const market = z.enum(MARKETS);
const price = z.number().finite().positive().max(1_000_000);
const unit = z.enum(UNITS);
const observation = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
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
  if (!TOOL_NAMES.includes(name)) throw new ContractError("unknown_tool", "未知工具，TW01 僅提供兩項工具。");
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

// SYNTHETIC MOCKS ONLY: not an Oracle prediction and not a frozen-model value.
export function quoteFixture() {
  return {
    ok: true, market_id: "中義市場", crop_id: "cabbage",
    price: 24.7, unit: "NTD_per_taiwan_jin",
    observed_date: "2026-10-01", public_data_cutoff: "2026-10-02",
    price_age_days_at_cutoff: 1,
    extra_source_field: { provenance: "synthetic-mock-only" },
  };
}
export function forecastFixture(unit = "NTD_per_taiwan_jin", observed = "2026-10-14") {
  const iso = (days) => new Date(Date.parse(observed + "T00:00:00Z") + days * 86400000).toISOString().slice(0, 10);
  return {
    crop_id: "cabbage", market_id: "中義市場",
    store_id: null, mode_executed: "without_last_week",
    input_observed_at: observed + "T12:00:00+08:00",
    model_version: "synthetic-mock-version-not-real",
    data_version: "synthetic-mock-data-not-real",
    public_data_cutoff: "2026-10-02",
    warnings: ["TEST FIXTURE ONLY — not a real ForecastEngine result"],
    results_with_last_week: [],
    results: [
      {
        horizon_days: 7, target_date: iso(7), direction: "flat",
        price_estimate: 33.1, price_estimate_unit: unit,
        relative_change_estimate: 0.0344,
        probability: null, interval_low: null, interval_high: null,
        target_scope: "store_price_estimate", validation_scope: "unvalidated",
        warnings: ["test: no calibrated interval"],
      },
      {
        horizon_days: 14, target_date: iso(14), direction: "down",
        price_estimate: 29.4, price_estimate_unit: unit,
        relative_change_estimate: -0.0811,
        probability: null, interval_low: null, interval_high: null,
        target_scope: "store_price_estimate", validation_scope: "unvalidated",
        warnings: ["test: no calibrated probability"],
      },
    ],
    untouched_extra_metadata: { warning_version: "mock", arbitrary_number: 7788 },
  };
}
export const VALID_TEST_ENV = {
  MCP_CLIENT_BEARER_TOKEN: "mcp-client-only-test-token-11111111111111111",
  FORECASTENGINE_API_TOKEN: "upstream-only-test-token-22222222222222222",
  FORECASTENGINE_BASE_URL: "https://oracle-fixture.invalid",
  UPSTREAM_TIMEOUT_MS: "100",
};
export const quoteArgs = { crop_id: "cabbage", market_id: "中義市場" };
export const forecastArgs = {
  ...quoteArgs, current_price: 32, price_unit: "NTD_per_taiwan_jin",
  observed_on: "2026-10-14",
};
export function quoteEnvelopeFixture() {
  return {
    tool: "get_market_quote",
    input_echo: { ...quoteArgs },
    normalized_request: null,
    query_date: "2026-10-14",
    engine_result: quoteFixture(),
    price_age_days_at_query: 13,
    fact_text: "TEST MOCK ONLY: 公開均價不是單店即時價格",
    limits: ["TEST MOCK ONLY: 公開均價不是單店即時價格"],
    unknown_metadata_preserved: { backend_version: "test-only" },
  };
}
export function forecastEnvelopeFixture(args = forecastArgs) {
  return {
    tool: "post_forecast",
    input_echo: { ...args },
    normalized_request: {
      crop_id: args.crop_id, market_id: args.market_id,
      current_price: args.current_price, price_unit: args.price_unit,
      observed_at: args.observed_on + "T12:00:00+08:00",
      mode: "without_last_week", store_id: null,
    },
    query_date: "2026-10-14",
    engine_result: forecastFixture(args.price_unit, args.observed_on),
    price_age_days_at_query: 12,
    fact_text: "TEST MOCK ONLY: not a real ForecastEngine forecast",
    limits: ["TEST MOCK ONLY: no real shop validation"],
    unknown_metadata_preserved: { backend_version: "test-only" },
  };
}
export function fakeResponse(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

"""代理人服務（T26）：自然語言查詢 → 確定性解析 → 有限工具 → 忠實回答。

後端可插換：
- RuleBackend：本機規則模板（無 LLM；回答只引用工具結果數字）。
- QwenBackend：SERVER 上的 Qwen（OpenAI 相容 chat API）。LLM 只負責「解釋」，
  工具參數由規則解析產生、工具結果直接放入訊息；系統提示（configs/agent_prompt.md）
  禁止編造數字/機率/原因。Qwen 不可用時自動降級 RuleBackend（T27 降級要求）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from .tools import AgentTools, ParsedQuery, ToolCallLimiter, parse_query

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[2] / "configs" / "agent_prompt.md"


def load_system_prompt(path: str | Path = DEFAULT_PROMPT_PATH) -> str:
    if Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return ""


class AgentBackend(Protocol):
    name: str

    def reply(self, parsed: ParsedQuery, tool_outputs: dict) -> str: ...


class RuleBackend:
    """規則模板回答：逐字引用工具結果，不生成任何工具外的數字或原因。"""

    name = "rule"

    _DIRECTION_TEXT = {"up": "可能上漲", "flat": "大致持平", "down": "可能下跌", "insufficient_data": "資料不足"}

    def reply(self, parsed: ParsedQuery, tool_outputs: dict) -> str:
        if parsed.missing:
            need = "、".join(parsed.missing)
            hint = "（例：高麗菜 一斤32）" if "計價單位" in need or "今天價格" in need else ""
            return f"還缺必要資訊：{need}。請補充品項、今天價格與計價單位{hint}。"
        if parsed.unit_non_comparable:
            return "「一顆／一把」這類計價沒有重量資訊，無法和市場每斤均價比較。請改輸入每台斤或每公斤價格。"

        forecast = tool_outputs.get("forecast")
        if not forecast or forecast.get("error"):
            err = (forecast or {}).get("error") or {}
            return f"目前無法提供預測：{err.get('message', '工具呼叫失敗')}。請確認品項與市場，或稍後再試。"

        crop_name = parsed.crop_text or parsed.crop_id
        lines = [
            f"{crop_name}（參考市場：{forecast['market_id']}），從今天 {forecast['input_observed_at'][:10]} 起算："
        ]
        results = forecast.get("results") or []
        ab = forecast.get("results_with_last_week") or []
        for r in results:
            pct = r.get("relative_change_estimate")
            pct_text = f"{pct:+.1%}" if isinstance(pct, (int, float)) else "—"
            est = r.get("price_estimate")
            est_text = f"，約 {est:g} 元" if isinstance(est, (int, float)) else ""
            lines.append(
                f"• {r['horizon_days']} 天後（{r['target_date']}）：{self._DIRECTION_TEXT.get(r['direction'], r['direction'])}（{pct_text}{est_text}）"
            )
        if ab:
            lines.append("有上週價格的對照（B，實驗性規則、未經同店驗證）：")
            for r in ab:
                pct = r.get("relative_change_estimate")
                pct_text = f"{pct:+.1%}" if isinstance(pct, (int, float)) else "—"
                lines.append(f"• {r['horizon_days']} 天後：{self._DIRECTION_TEXT.get(r['direction'], r['direction'])}（{pct_text}）")
        lines.append(
            f"（公開行情截止 {forecast['public_data_cutoff']}；模型 {forecast['model_version']}；點估計僅供參考，非同店驗證）"
        )
        return "\n".join(lines)


class QwenBackend:
    """SERVER Qwen 後端：OpenAI 相容 /chat/completions；只做解釋層。"""

    name = "qwen"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "AIOT_QWEN_API_KEY",
        timeout: float = 30.0,
        prompt_path: str | Path = DEFAULT_PROMPT_PATH,
    ):
        self.base_url = base_url or os.environ.get("AIOT_QWEN_BASE_URL", "")
        self.model = model or os.environ.get("AIOT_QWEN_MODEL", "")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.system_prompt = load_system_prompt(prompt_path)

    def available(self) -> bool:
        return bool(self.base_url and self.model)

    def reply(self, parsed: ParsedQuery, tool_outputs: dict) -> str:
        if not self.available():
            return RuleBackend().reply(parsed, tool_outputs)
        import urllib.error
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        "使用者問題與工具結果如下。請依系統規則回答，只能引用工具結果的數字。\n\n"
                        f"工具結果（JSON）：\n{json.dumps(tool_outputs, ensure_ascii=False, default=str)}"
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        key = os.environ.get(self.api_key_env)
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            # Qwen 失敗降級：手機仍顯示真實模型結果（T27 要求）
            return RuleBackend().reply(parsed, tool_outputs)


def handle_agent_query(
    engine,
    query: str,
    store_id: str | None = None,
    backend: AgentBackend | None = None,
    today=None,
) -> dict:
    """完整代理人流程：解析→工具→回答；回傳含匿名追蹤紀錄（T26 驗收）。"""
    backend = backend or RuleBackend()
    parsed = parse_query(query, today=today)
    tools = AgentTools(engine)
    limiter = ToolCallLimiter()
    trace: list[dict] = []

    tool_outputs: dict = {}
    # 工具1：若有品項，先查最新行情（供回答引用；失敗不阻斷）
    if parsed.crop_id and parsed.market_id and limiter.check():
        quote = tools.get_market_quote(parsed.crop_id, parsed.market_id)
        tool_outputs["market_quote"] = quote
        trace.append({"tool": "get_market_quote", "args": {"crop_id": parsed.crop_id, "market_id": parsed.market_id}, "ok": quote.get("ok", False)})
    elif parsed.crop_id and not parsed.market_id and limiter.check():
        quote = tools.get_market_quote(parsed.crop_id, "中義市場")
        tool_outputs["market_quote"] = quote
        trace.append({"tool": "get_market_quote", "args": {"crop_id": parsed.crop_id, "market_id": "中義市場（預設）"}, "ok": quote.get("ok", False)})

    # 工具2：預測（必要欄位齊才呼叫）
    req = parsed.to_forecast_request(store_id=store_id)
    if req is not None and limiter.check():
        forecast = tools.post_forecast(req)
        tool_outputs["forecast"] = forecast
        trace.append({"tool": "post_forecast", "args": {k: req.get(k) for k in ("crop_id", "market_id", "current_price", "price_unit", "mode")}, "ok": not forecast.get("error")})
    else:
        tool_outputs["forecast"] = None

    answer = backend.reply(parsed, tool_outputs)
    return {
        "backend": getattr(backend, "name", "unknown"),
        "parsed": {
            "crop_id": parsed.crop_id,
            "current_price": parsed.current_price,
            "price_unit": parsed.price_unit,
            "market_id": parsed.market_id,
            "previous_price": parsed.previous_price,
            "mode": (req or {}).get("mode"),
            "missing": parsed.missing,
            "unit_non_comparable": parsed.unit_non_comparable,
        },
        "tool_trace": trace,
        "answer": answer,
    }

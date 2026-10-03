# Hermes Agent 官方查證與隔離安裝探測（第四輪前置）

日期：2026-10-04。依據：使用者指示（第四輪前置）、[代理人方向](../AGENT_RUNTIME_DIRECTION.md) 第 2、3、6 節、決策 D41。
探測機器：本工作機（Windows 10 19045，Python 3.12.10）。隔離環境：`%TEMP%\hermes_probe` 獨立 venv，探測完成後已刪除。
證據目錄：[outputs/audits/round4_glm_api/hermes_probe/](../../outputs/audits/round4_glm_api/hermes_probe/)（安裝日誌、API 探測輸出 JSON／文字）。

## 結論摘要

1. **官方 PyPI 套件存在且可安裝**：`hermes-agent` 0.19.0（2026-07-20 發布，Nous Research 官方 Trusted Publishing），Python `>=3.11,<3.14`，MIT。本機 3.12.10 隔離 venv 安裝成功、可 import、可離線建構 agent。
2. **程式化 Python API 存在**：`from run_agent import AIAgent`（注意：套件名 `hermes-agent`、import 名 `run_agent`；`import hermes_agent` 會失敗）。`AIAgent(model, api_key, base_url, enabled_toolsets, ...)` 離線可建構，內部用官方 `openai` SDK（chat.completions）。
3. **GLM 有官方 provider**：provider 名 `zai`，環境變數 `GLM_API_KEY`（備援 `ZAI_API_KEY`／`Z_AI_API_KEY`）、`GLM_BASE_URL` 可覆寫端點；框架自動探測 Z.AI 全球／中國／Coding 端點。自架 OpenAI 相容端點（未來 Qwen3.8-27B）直接給 `base_url` 即可，實測 client 為 `openai.OpenAI`。
4. **工具白名單機制實測有效**：`enabled_toolsets`／`disabled_toolsets` 參數與 `get_tool_definitions()` 過濾實測通過（白名單只含自訂 echo 工具）。自訂工具兩條路：內部 `tools.registry.register()`（實測可用但屬內部 API）或 MCP（有正式文檔與逐伺服器 `tools.include` 白名單）。
5. **主要阻礙不是「不能裝」，而是安全與文件落差**：`hermes-agent` entry point 無 `--help` 處理、會直接啟動真連線並讀取使用者全域設定中的金鑰（本次探測意外觸發一次，已如實記錄）；文檔多處過時（說無 wheel 要 clone）；內建預設工具含 terminal／browser／execute_code，本案必須白名單＋`HERMES_HOME` 隔離。

---

## 1. 官方查證（全部 2026-10-04 實讀）

| 來源 | 讀取狀態 | 重點 |
| --- | --- | --- |
| https://github.com/NousResearch/hermes-agent | 讀取成功 | 安裝以 installer script 為主（`curl …/install.sh \| bash`；Windows `iex (irm …/install.ps1)`）；CLI 為主要介面（`hermes`、`hermes gateway`）；MIT；README 提到 installer 委派 Python **3.14**／Node 等依賴 |
| https://hermes-agent.nousresearch.com/docs/ | 讀取成功 | 入門頁僅安裝與 `hermes setup --portal`；無 Python API 細節；完整 TOC 由 `/docs/llms.txt` 取得 |
| https://hermes-agent.nousresearch.com/docs/guides/python-library | 讀取成功 | 程式化用法：`from run_agent import AIAgent`、`agent.chat(msg)`、`agent.run_conversation(...)`、`enabled_toolsets=["web"]`／`disabled_toolsets=["terminal"]`。**注意：此頁聲稱「沒有發布 wheel、要 git clone」——與 PyPI 實況不符，屬過時內容**（見第 6 節） |
| https://hermes-agent.nousresearch.com/docs/integrations/providers/ | 讀取成功 | `zai`／GLM 在支援表；`GLM_API_KEY` 寫在 `~/.hermes/.env`（provider: zai）；`hermes chat --provider zai --model glm-5`；`GLM_BASE_URL` 覆寫；自訂 OpenAI 相容端點用 `model:` 區塊（`default`／`provider`／`base_url`／`api_key`／`key_env`／`context_length`）或 `providers:` dict（`api`、`key_env`、`transport: chat_completions`…）；設定檔為 YAML：`~/.hermes/config.yaml` |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/tools 與 /docs/reference/toolsets-reference | 讀取成功 | 內建 toolset：web、terminal、browser、cronjob、file、code_execution…；`toolsets:`（config.yaml）＋`custom_toolsets:`；CLI `hermes chat --toolsets web,file`；互動 `hermes tools`、會話內 `/tools disable browser`；`safe` toolset＝唯讀研究＋媒體生成 |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp | 讀取成功 | `mcp_servers:`（config.yaml）支援 stdio（`command`/`args`/`env`）與 HTTP（`url`/`headers`）；逐伺服器白名單 `tools.include: [create_issue, list_issues]`（include 優先於 exclude，支援 fnmatch）；`enabled: false` 整伺服器停用 |
| https://pypi.org/project/hermes-agent/ | 讀取成功 | 套件 `hermes-agent` **0.19.0**（2026-07-20）；發布者 Nous Research（Trusted Publishing via GitHub Actions，維護者 dakota-nous、sidbin）；`Requires-Python >=3.11,<3.14`；MIT |

查證日期均為 2026-10-04；以上為頁面實讀內容，非快照延用。

## 2. 隔離安裝實測

- 命令：`python -m venv %TEMP%\hermes_probe` → `%TEMP%\hermes_probe\Scripts\python.exe -m pip install hermes-agent`
- 結果：**成功**。安裝 `hermes-agent-0.19.0`；完整日誌見證據 `install_log.txt`。
- 依賴（核心 Requires-Dist，節錄）：`openai==2.24.0`、`httpx[socks]==0.28.1`、`pydantic`、`pyyaml`、`ruamel.yaml`、`fastapi`、`uvicorn`、`fire`、`tenacity`、`rich` 等。**沒有 litellm、沒有 anthropic／google SDK**（那些是 optional extras）→ LLM 交談走官方 `openai` 套件（chat.completions 為主，另有 `anthropic_messages`／`bedrock_converse` api_mode 分支）。
- `hermes --version` 實測輸出：`Hermes Agent v0.19.0 (2026.7.20) · upstream aaf96885`、`Python: 3.12.10`、`OpenAI SDK: 2.24.0`（證據 `cli_version_and_incident.txt`）。
- Console entry points（dist-info 實測）：`hermes`＝hermes_cli.main、`hermes-acp`＝acp_adapter.entry、`hermes-agent`＝run_agent.main。
- 探測後暫存 venv 已刪除（`%TEMP%\hermes_probe` 不存在）。

### 意外事件（如實記錄）

執行 `hermes-agent.exe --help` 意圖查說明時，**該 entry point 沒有 --help 處理，直接啟動完整 agent 對話**：初始化 agent、顯示從使用者既有環境找到的遮罩金鑰（`sk-***（遮罩）`，來源未查明，值未讀取、未保存）、載入 31 個工具（含 terminal／browser）、開始 `API call #1/10`；輸出被 `head -15` 截斷後程序終止，事後確認無殘留進程。這次單一命令可能已發出一次真實 HTTP 請求，違反「僅離線」規則——成因是 entry point 行為而非刻意測試。教訓（已納入第 6 節阻礙）：整合與測試時必須固定 `HERMES_HOME` 到專案隔離目錄、控制環境變數，且不要用 `hermes-agent` entry point 當查詢介面。

## 3. 實際 API 表面（inspect 實測，證據 `probe2_api_surface.txt`）

Import：`import run_agent` 成功（site-packages 單檔 `run_agent.py`，6,650 行 + `hermes_cli/`、`tools/`、`agent/`、`providers/` 等頂層套件）；`import hermes_agent` **失敗**（`ModuleNotFoundError`）——文檔與原始碼一致用 `run_agent`。

### AIAgent（`run_agent.AIAgent`，定義於 `agent/agent_init.py`）

`__init__` 重點參數（完整簽名見證據檔；官方 python-library 頁有部分對照表）：

| 參數 | 型別／預設 | 說明（原始碼/文檔） |
| --- | --- | --- |
| `model` | str, `""` | 模型名；空時從 hermes 設定解析 |
| `provider` | str, None | 如 `"zai"`、`"custom"` |
| `api_key` / `base_url` | str, None | 明確憑證；**兩者同時給即可直接建構 client，不需要全域設定**（agent_init.py「Explicit credentials from CLI/gateway — construct directly」分支） |
| `api_mode` | str, None | 如 `chat_completions`／`anthropic_messages`／`bedrock_converse` |
| `enabled_toolsets` / `disabled_toolsets` | List[str], None | **工具白名單／黑名單** |
| `max_iterations` | int, 90（文檔頁寫 500，0.19.0 實測 90） | 代理迴圈上限 |
| `quiet_mode` | bool, False | 嵌入時必開（文檔要求） |
| `save_trajectories` | bool | JSONL 軌跡（對應 T27 工具追蹤要求） |
| `skip_context_files` / `skip_memory` | bool | 跳過 AGENTS.md 載入／常駐記憶（無狀態端點建議開） |
| `providers_allowed` / `providers_ignored` / `providers_order` | List[str] | provider 過濾 |
| `request_overrides` / `prefill_messages` / `fallback_model` / `session_id` / 回調系列 | — | 進階控制 |

方法（`inspect.getmembers` 實測）：`chat(message, stream_callback=None) -> str`；`run_conversation(user_message, system_message=None, conversation_history=None, task_id=None, …) -> Dict`（回傳含 `final_response`／`messages`）；`switch_model(new_model, new_provider, api_key='', base_url='', api_mode='')`；`interrupt`／`steer`／`close`／`reset_session_state`／`get_rate_limit_state` 等。

### 工具系統

- 登錄檔：`tools/registry.py` 的 `ToolRegistry`，singleton `registry`（registry.py:765）。註冊 API（registry.py:365-379）：

```python
from tools.registry import registry
registry.register(
    name="echo_probe",
    toolset="probe",                      # 自訂 toolset 名
    schema={"type": "function", "function": {...OpenAI 格式...}},
    handler=my_callable,                  # 也可 is_async=True
)
```

- 工具定義查詢：`model_tools.get_tool_definitions(enabled_toolsets=None, disabled_toolsets=None, quiet_mode=False, …)`（model_tools.py:279），回傳 OpenAI 格式工具定義；所有工具必須歸屬 toolset 才可被選用。
- 離線目錄實測（無任何金鑰，證據 `probe5_toolset_map.json`）：28 個工具可用（terminal、browser_*、execute_code、patch、write_file…全在）；金鑰齊全的環境為 31 個（差異為願景／影像等 gated 工具）。

### MCP 接入（文檔，未實測連線）

`~/.hermes/config.yaml`：`mcp_servers:` 下 stdio（`command`/`args`/`env`）或 HTTP（`url`/`headers`）伺服器；逐伺服器白名單 `tools.include: [...]`（include 優先、支援 glob）、`enabled: false` 停用；`hermes mcp add` 也可。菜價工具若走 MCP，白名單語法已有正式文檔支援。

## 4. GLM 與自架 Qwen 端點設定對照

| 面向 | GLM（官方 provider） | 自架 Qwen3.8-27B（OpenAI 相容） |
| --- | --- | --- |
| provider 名 | `zai`（別名 `glm`／`z-ai`／`z.ai`／`zhipu`，providers.py:255-259） | `custom`（或不設 provider、直接給 base_url） |
| 金鑰 | 環境變數 `GLM_API_KEY`（備援 `ZAI_API_KEY`、`Z_AI_API_KEY`），providers.py:105-109 | 通常不需要；`api_key="x"` 佔位即可（vLLM/ollama 相容） |
| 端點 | 自動探測：`https://api.z.ai/api/paas/v4`（全球）、`https://open.bigmodel.cn/api/paas/v4`（中國）、`…/api/coding/paas/v4`（Coding Plan 變體，auth.py:625-628）；`GLM_BASE_URL` 可覆寫 | `base_url` 直接指定，如 `http://<server_3090>:8000/v1` |
| transport | `openai_chat`（openai SDK chat.completions） | 同左（`chat_completions`） |
| 程式化寫法（實測） | `AIAgent(model="glm-5", api_key=…, base_url="https://api.z.ai/api/paas/v4")` 或 `agent.switch_model("glm-5", "zai", api_key=…)` → 實測 provider=zai、client.base_url 正確 | `AIAgent(model="Qwen3.8-27B", api_key="dummy", base_url="http://127.0.0.1:9/v1")` → 實測建構成功，client 型別 `openai.OpenAI` |
| config.yaml 寫法（providers 頁） | `model: {default: glm-5, provider: zai}` ＋ `.env` 金鑰 | `model: {default: <model>, provider: custom, base_url: http://…/v1, api_key: …}` 或 `providers:` dict（`api`、`key_env`、`transport: chat_completions`） |

Coding Plan 專用端點與一般 API 的差異（[代理人方向](../AGENT_RUNTIME_DIRECTION.md) 第 5 節）在 Hermes 內呈現為不同 base_url 變體；實際帳戶可用哪個端點仍待使用者方案核對，本輪未打任何真 GLM 請求。

## 5. 工具白名單與停用內建工具（離線實測，證據 `probe3/probe4_*.json`）

- **白名單**：`registry.register(toolset="probe", …)` 掛 echo 工具後，`get_tool_definitions(enabled_toolsets=["probe"])` 只回 `["echo_probe"]`；terminal／browser／cronjob 全部不出現。
- **建構參數**：`AIAgent(enabled_toolsets=["probe"], disabled_toolsets=["terminal","browser","cronjob"], …)` 同時支援正面表列與黑名單。
- **config 層**：`toolsets:`（平台預設）＋`custom_toolsets:`（自訂群組）；CLI `--toolsets`；MCP 逐伺服器 `tools.include`。
- 本案建議：`enabled_toolsets` 只列自訂菜價 toolset（及必要唯讀工具），不使用 `hermes-cli` 預設 preset（其含 terminal／browser／cronjob／computer_use）。

## 6. 整合建議路徑與具體阻礙

### 建議路徑

1. 安裝：專案另建獨立 venv（Python 3.11–3.13；本機 3.12.10 驗證可跑）`pip install hermes-agent==0.19.0`，不混入既有 `.venv` 之前先確認相依無衝突（openai 2.24.0 是 pin 死的版本）。
2. GLM 先行：`HERMES_HOME` 指向專案隔離目錄；provider `zai`＋`GLM_API_KEY`（來源依使用者實際平台：Z.AI 或 BigModel，必要時 `GLM_BASE_URL` 指定）；agent 以 `enabled_toolsets` 白名單建立。
3. 菜價工具：首選 MCP stdio server 包 ForecastEngine（正式文檔＋`tools.include` 白名單＋與框架版本解耦）；或評估 `registry.register` 原生註冊（較輕但屬內部 API，版本升級風險自負）。
4. Qwen 切換：同一段程式只換 `base_url`／`model`（`switch_model` 實測可用）；符合「配置切換、不自動 fallback」要求。

### 具體阻礙與風險（附證據）

| # | 阻礙／風險 | 證據 |
| --- | --- | --- |
| 1 | **entry point 安全**：`hermes-agent` 無 `--help`，任何 argv 可能直接啟動真連線；未隔離時會讀使用者全域設定並找到真實金鑰 | `cli_version_and_incident.txt`（本次意外觸發記錄） |
| 2 | **文檔過時**：python-library 頁稱「無 wheel、要 git clone」，實際 PyPI 0.19.0 可直接 pip 安裝；README installer 提 Python 3.14 但 PyPI 上限 `<3.14` | PyPI 實讀 vs python-library 頁；probe1 實測 |
| 3 | **建構依賴全域設定**：只給 `model`＋`api_key` 而無 `provider`／`base_url` 時，讀 `~/.hermes/config.yaml`，無設定即 `RuntimeError: No LLM provider configured` | probe3 JSON |
| 4 | **自訂工具無公開承諾 API**：`registry.register` 是內部機制（docstring 自述 module-import 時呼叫）；正式擴充介面是 MCP／plugins | tools/registry.py 原始碼 |
| 5 | **輔助服務嘗試**：建構／工具裝配時對 openrouter／nous 輔助端點做可用性探測（無金鑰時印 unhealthy 並降級，不擋建構；但難保零網路流量） | probe3/probe5 stderr |
| 6 | **預設工具面大**：離線即有 terminal／browser／execute_code／file 寫入；本案必須白名單，且不可用 `--toolsets all` | probe5_toolset_map.json |
| 7 | Python 版本窗口 `>=3.11,<3.14`：未來升 3.14 需等上游 | PyPI METADATA 實測 |

## 7. 未驗證項（本輪邊界）

- 真 GLM／zai API 呼叫（含 tool_calls 完整往返、glm-5 實際行為）——未打任何刻意請求。
- 真自架 Qwen3.8-27B 端點（SERVER_3090 尚未提供）。
- `chat()`／`run_conversation()` 端到端輸出（需真 API）。
- MCP server 實際接入與 `tools.include` 行為（僅文檔＋`mcp_config.py` 存在性，未連線）。
- `hermes gateway`／Telegram 等訊息平台、api-server 功能（未測）。
- 意外事件中那次 `API call #1` 是否真的送達外部端點（無回應可查）。

## 8. 證據清單

`outputs/audits/round4_glm_api/hermes_probe/`：`install_log.txt`（pip 安裝全紀錄）、`pip_freeze.txt`、`probe1_import_version.txt`（import／版本）、`probe2_api_surface.txt`（AIAgent 完整簽名與方法）、`probe3_offline_smoke.txt/.json`（echo 註冊＋白名單＋首次建構錯誤）、`probe4_offline_smoke2.txt/.json`（zai overlay／離線建構／switch_model）、`probe5_toolset_map.txt/.json`（28 工具目錄）、`cli_version_and_incident.txt`（hermes --version 與 --help 意外事件）。

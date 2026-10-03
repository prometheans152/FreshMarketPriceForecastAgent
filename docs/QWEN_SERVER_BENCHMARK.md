# Qwen 代理人型號核實與 3090 實測（T25）

本檔分兩部分：**型號核實（本輪完成，2026-10-03）** 與 **3090 實測（HOLD：待 SERVER）**。依 `docs/SERVER_INVENTORY.md`，SERVER 的 OS、位址、CUDA 版本尚未取得，實測欄位全部保留，不虛構數值。

---

## 一、型號核實（本輪完成，2026-10-03）

### 1.1 核實問題

使用者口述（D32）：「代理人可能到時會用3090跑一個QWEN 3.8」。RTX 3090 為 24GB VRAM。需向官方來源確認：

1. 「Qwen 3.8／Qwen3.8」是否為官方可取得的模型名稱？
2. 2026-10 時點官方有無適合單卡 24GB 的中尺寸（約 4B–14B）候選？
3. 官方推薦的推論框架與工具呼叫支援文檔位置？

### 1.2 查核方法與來源限制

- 只採用官方來源：GitHub `QwenLM` 組織、Hugging Face `Qwen` 官方組織的模型卡與 collection、（舊）官方 blog `qwenlm.github.io`。第三方文章僅當線索，全部回到官方頁確認。
- 舊官方 blog `https://qwenlm.github.io/blog/` 最後一篇文章為 2025-09-23（Qwen3Guard），之後停更並導向 `qwen.ai`；`qwen.ai/blog` 為 JS 動態頁，本輪工具抓不到內文，故 2026 年公告以 GitHub README 與 HF 模型卡為準。此為已查證的來源限制，非未查。
- 查核日期：2026-10-03。以下「查得」均指當日以 WebFetch 直接讀取官方頁面所得。

### 1.3 「Qwen 3.8」核實結論

**結論：「Qwen3.8」確實是官方系列名稱（2026-08 發布），但 Qwen3.8 開源系列沒有 4B–14B 的模型；最小的 Qwen3.8 為 27B dense，其官方權重（BF16 約 55.5GB、官方 FP8 約 28GB）超過單卡 24GB，無法直接在 RTX 3090 上以官方檢查點執行。**

查得證據（均為官方頁面，2026-10-03 讀取）：

| 官方證據 | 內容 |
| --- | --- |
| GitHub [QwenLM/Qwen3.8](https://github.com/QwenLM/Qwen3.8)（組織 pinned repo） | 「the large language model series developed by Qwen team, Alibaba Group」；README 列出 Qwen3.8 系列僅兩個開源檢查點：Qwen3.8-2.4T-A95B（MoE 旗艦，2026-08-12）與 Qwen3.8-27B（2026-08-14） |
| HF 官方 collection [qwen38](https://huggingface.co/collections/Qwen/qwen38) | 僅 4 個檢查點：Qwen3.8-2.4T-A95B（BF16／FP8）、Qwen3.8-27B（BF16／FP8）。**無小於 27B 的 Qwen3.8** |
| HF [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) 模型卡 | dense、約 27.78B 參數、BF16 safetensors 約 55.5GB（18 分片）、image-text-to-text（原生影像與影片理解）、Apache-2.0、原生 262,144 context（YaRN 可至 1M）、chat template 內建 `<tool_call>` 工具呼叫格式 |
| HF [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) 模型卡 | 2026-08-24 建立的架構預覽，約 180B 總參數 MoE（125B／6B 啟動＋51B n-gram embedding＋4B MTP）、授權 `qwen-community-1.0`（非 Apache 2.0）、總權重遠超 24GB |
| HF `Qwen` 組織頁（依修改時間排序） | 可見 Qwen3.8-27B、Qwen3.8-2.4T-A95B、Qwen3.8-Flash-Next 及各自 FP8；未見其他 Qwen3.8 尺寸 |

「Qwen 3.8」的可能原意與對應（供使用者確認，不暗自換型號）：

1. 指 **Qwen3.8 系列**：官方存在，但 3090 單卡放不下官方權重的最小成員（27B）。
2. 指「Qwen3 的 8B」即 **Qwen3-8B**：官方存在（2025-04-27，Apache-2.0），24GB 可跑。
3. 指約 8B 級的最新官方模型：即 **Qwen3.5-9B**（2026-03-02，Apache-2.0），24GB 可跑（BF16 約 19.3GB，緊）。

網路第三方有稱「27B 的 FP8 常被認定 24GB 可行」或「27B 約 15GB」——後者是社群 INT4 量化估算，非官方檢查點；官方 FP8 以 1 byte/參數估算約 28GB，已超過 24GB。本輪不以第三方說法當證據，3090 實測前不定案。

### 1.4 單卡 24GB（約 4B–14B 級）官方候選清單

官方仍有提供、且 BF16 權重可放進 24GB 的候選（顯存為依參數量×每參數 bytes 的推算，官方卡未給 VRAM 需求數字；KV cache 另計）：

| # | 官方名稱 | 參數量 | 架構／模態 | 發布 | 授權 | Context | 工具呼叫證據 | BF16 權重推算 | 來源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Qwen3.5-9B | 9.65B（BF16 safetensors 約 19.3GB） | dense-hybrid（Gated DeltaNet＋Gated Attention）、視覺語言（image-text-to-text） | 2026-03-02 | Apache-2.0 | 262,144（YaRN 至 1,010,000） | 模型卡明文「Qwen3.5 excels in tool calling capabilities」，並建議 Qwen-Agent／MCP | 約 19.3GB（緊，可留少量 KV；vLLM `--language-model-only` 可略過視覺編碼器省顯存） | [HF 模型卡](https://huggingface.co/Qwen/Qwen3.5-9B) |
| 2 | Qwen3.5-4B | 約 4.66B（BF16 約 9.3GB） | 同上、視覺語言 | 2026-03-02 | Apache-2.0 | 262,144（YaRN 至 1,010,000） | 同上：chat template 內建 tools 區段、Qwen-Agent／MCP | 約 9.3GB（寬裕，KV 空間大） | [HF 模型卡](https://huggingface.co/Qwen/Qwen3.5-4B) |
| 3 | Qwen3-8B | 8.2B（BF16 約 16.4GB） | dense、純文字 | 2025-04-27 | Apache-2.0 | 32,768（YaRN 131,072） | 模型卡明文 agent 能力與 Qwen-Agent 整合；chat template 支援 `<tools>`／`<tool_call>` | 約 16.4GB（可行） | [HF 模型卡](https://huggingface.co/Qwen/Qwen3-8B) |
| 4（參照） | Qwen3.8-27B（含官方 -FP8） | 約 27.78B | dense、視覺語言 | 2026-08-14 | Apache-2.0 | 262,144（YaRN 至 1,000,000） | 模型卡 agentic 基準與 `<tool_call>` 模板 | BF16 約 55.5GB／FP8 約 28GB → **超過 24GB，官方權重不可行** | [HF 模型卡](https://huggingface.co/Qwen/Qwen3.8-27B) |

更小的官方同系列檢查點（低於 4B，備查）：Qwen3.5-2B、Qwen3.5-0.8B（2026-03-02，GitHub README 列出）。

已排除（單卡 24GB 不可行或授權不符）：

- Qwen3.8-2.4T-A95B／-FP8：2.4T 總參 MoE 旗艦，總權重遠超 24GB。
- Qwen3.8-Flash-Next：約 180B 總參 MoE 預覽，且授權 `qwen-community-1.0` 非 Apache 2.0。
- Qwen3.5-397B-A17B、Qwen3.5-122B-A10B、Qwen3.5-35B-A3B、Qwen3.6-35B-A3B、Qwen3-Coder-30B-A3B：MoE 總參數量使 BF16／FP8 權重皆超 24GB。
- Qwen3.5-27B、Qwen3.6-27B：dense 27B，與 Qwen3.8-27B 同樣超卡。

### 1.5 官方推薦推論框架與工具呼叫文檔位置

| 框架 | 官方支援狀態與文檔位置 |
| --- | --- |
| vLLM | [QwenLM/Qwen3.8 README](https://github.com/QwenLM/Qwen3.8) serving 段：`vllm serve "Qwen/Qwen3.8-27B"`，工具呼叫用 `--tool-call-parser qwen3_coder --enable-auto-tool-choice`。Qwen3.5-9B 模型卡：生產建議 vLLM（需 main 分支版本）。Qwen3-8B 卡：vLLM ≥ 0.8.5 |
| SGLang | 同上 README：`python3 -m sglang.launch_server --model-path ...`；Qwen3.5-9B 卡列為生產建議之一 |
| llama.cpp | README 提 Qwen3.5 系列有 GGUF 支援；各官方模型卡本身為 BF16 safetensors（`isQuantized: false`），llama.cpp 使用「community quantizations」連結（非官方量化檔） |
| Ollama | 官方 README 與模型卡未列為建議框架，僅在「可用於 llama.cpp／Ollama／LM Studio」的社群量化說明中出現 |
| transformers | Qwen3-8B 卡要求 ≥ 4.51.0；Qwen3.5-9B／Qwen3.8-27B 卡列直接載入方式 |
| Qwen-Agent | Qwen3.5 與 Qwen3 模型卡建議的官方 agent 框架（含 MCP 支援） |

### 1.6 建議與理由

1. **首選候選：Qwen3.5-9B**（Apache-2.0）。理由：2026-10 時點官方提供中、最接近「8B 級」的最新中型模型；模型卡明文支援工具呼叫與 Qwen-Agent／MCP；262K context 對本案（少量中文文字＋結構化工具參數）綽綽有餘；BF16 約 19.3GB 在 24GB 內，且可用 vLLM `--language-model-only` 略過視覺編碼器換取 KV 空間。
2. **備選一：Qwen3.5-4B**（Apache-2.0）：同代同授權，顯存寬裕、延遲更低；若 9B 實測 KV 不足或速度不夠再降。
3. **備選二：Qwen3-8B**（Apache-2.0）：較舊但純文字、工具呼叫生態最成熟（vLLM tool parser、Qwen-Agent 文件齊），作為 Qwen3.5 hybrid 架構在 SERVER 端框架版本不合時的退路。
4. **Qwen3.8-27B 不列入 3090 首選**：官方權重（BF16／FP8）超過 24GB；除非使用者接受社群 INT4 量化並另行驗證工具呼叫正確率，或 SERVER 實測證明可行，否則不採。此為「使用者所稱 Qwen3.8 與 3090 條件衝突」的具體原因，須回報使用者知悉。
5. 所有候選在 SERVER（OS／CUDA 未知）實測載入、峰值顯存、延遲、中文品項理解與工具參數正確率後鎖定（見下半部）。

---

## 二、3090 實測（HOLD：待 SERVER）

**狀態：HOLD——依 `docs/SERVER_INVENTORY.md`，SERVER OS、位址、CUDA／驅動版本未取得，以下欄位尚未執行、無任何數值。**

待測項目（取得 SERVER 後填入，證據放 `outputs/server/qwen_benchmark/`）：

| 項目 | 內容 | 結果 |
| --- | --- | --- |
| 環境 | OS／驅動／CUDA／框架版本 | 未測 |
| 載入 | 各候選實際載入成功與否、啟動時間 | 未測 |
| 峰值顯存 | 載入後與推論中 `nvidia-smi` 峰值（含 KV cache 設定） | 未測 |
| 延遲 | 首 token 與完整回應時間（中文菜價查詢句） | 未測 |
| 中文品項理解 | 菜名／規格／單位抽取正確率（甘藍、空心菜、元/臺斤等） | 未測 |
| 工具參數正確率 | 對 `POST /forecast` 等工具的 JSON 參數生成正確率 | 未測 |
| 並存 | 與菜價模型推論服務同卡的顯存分配 | 未測 |

驗收門檻（依 TASKS T25）：真權重載入與實際請求輸出（版本、量化、顯存、延遲、工具案例）才可標 PASS；僅官方頁可讀不算實測通過。

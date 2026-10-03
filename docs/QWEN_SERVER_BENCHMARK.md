# Qwen 代理人型號核實與 3090 實測（T25）

本檔分兩部分：**型號核實（2026-10-03 第一輪；同日依第二輪獨立審查 F09 修訂）** 與 **3090 實測（HOLD：待 SERVER）**。依 `docs/SERVER_INVENTORY.md`，SERVER 的 OS、位址、CUDA 版本尚未取得，實測欄位全部保留，不虛構數值。

**F09 修訂摘要（2026-10-03）**：第二輪獨立審查（`docs/reviews/ROUND2_7fdb43b_REVIEW.md` F09）指出原「Qwen3.8 跑不動 3090」結論過度概括。本輪重新讀取官方與實作者來源後修訂：官方 BF16／FP8 檢查點確實無法全放 24GB，但 **27B GGUF 4-bit（實作者資料約 16–19GB）是值得 3090 實機測試的候選，尚未實測**；使用者的 Qwen3.8 候選不被排除，列為優先實測對象。

---

## 一、型號核實（2026-10-03；F09 修訂輪）

### 1.1 核實問題

使用者口述（D32）：「代理人可能到時會用3090跑一個QWEN 3.8」。RTX 3090 為 24GB VRAM（Ampere 架構）。需確認：

1. 「Qwen 3.8／Qwen3.8」是否為官方可取得的模型名稱？
2. 2026-10 時點官方有無適合單卡 24GB 的中尺寸（約 4B–14B）候選？
3. 官方推薦的推論框架與工具呼叫支援文檔位置？
4. **（F09 新增）27B 的 GGUF 4-bit 社群量化在 24GB 是否值得實測？NVFP4 數字是否適用 3090？**

### 1.2 查核方法、證據分類與連結讀取狀態

證據分三類，全檔一致標示：

- **官方證據**：GitHub `QwenLM` 組織、Hugging Face `Qwen` 官方組織的模型卡與 collection。
- **實作者證據**：Unsloth 官方文件（`unsloth.ai/docs`）與其 GGUF 工件（HF `unsloth` 組織）。這是實作者資料，**不是 Qwen 官方發布的量化權重**。
- **未驗證估計**：參數量 × 每參數 bytes 的推算、第三方文章說法。僅當線索，不當結論。

本輪（F09 修訂輪，2026-10-03）連結讀取狀態：

| # | 連結 | 證據類別 | 讀取狀態 | 本輪取得要點 |
| --- | --- | --- | --- | --- |
| 1 | [github.com/QwenLM/Qwen3.8](https://github.com/QwenLM/Qwen3.8) | 官方 | 完整 | Local Use 段明列 llama.cpp（「Look for models ending with GGUF on Hugging Face Hub」），並連結 Unsloth 量化指南（「the Qwen3.8 guide」→ `unsloth.ai/docs/models/qwen3.8`）；系列開源檢查點僅 2.4T-A95B（2026-08-12）與 27B（2026-08-14） |
| 2 | [unsloth.ai/docs/models/qwen3.8](https://unsloth.ai/docs/models/qwen3.8) | 實作者 | 完整 | 27B 4-bit 需求 16–19GB（列 RTX 5080、4090 或 24GB RAM 的 Mac）；「For older GPUs, our GGUFs work well!」；NVFP4 需 Blackwell（RTX 50X、DGX Spark、B200、B300），宣稱約 1.5× BF16；量化表：1-bit 7–8GB／2-bit 9–11GB／3-bit 12–14GB／4-bit 16–19GB／6-bit 23–26GB／8-bit 31GB／BF16 56GB；MTP 另需 1–2GB；建議 4-bit 變體為 UD-Q4_K_XL |
| 3 | [huggingface.co/unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) | 實作者工件 | 完整 | `Qwen3.8-27B-UD-Q4_K_M.gguf` 16.5GB、`Qwen3.8-27B-UD-Q4_K_XL.gguf` 17.6GB（範圍 UD-IQ1_S 6.19GB 至 BF16 54.7GB；另有 mmproj 視覺檔與 MTP Q4_0 變體）；Apache-2.0；基底模型 `Qwen/Qwen3.8-27B`；示範 `llama serve -hf unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`；架構標籤 `qwen35`，需較新 llama.cpp |
| 4 | [huggingface.co/Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | 官方 | 完整 | BF16 總檔 55,563,118,992 bytes（約 55.6GB）、18 分片；27,781,427,952 參數；原生 262,144 context（YaRN 至 1M）；Apache-2.0；模型卡附「Browse Quantizations」連向 llama.cpp／Ollama／LM Studio 相容之社群量化 |
| 5 | [huggingface.co/Qwen/Qwen3.8-27B-FP8](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) | 官方 | 完整 | 總檔 30,867,004,263 bytes（約 30.9GB，≈28.7GiB）；F8_E4M3 block-size 128 細粒度量化；**卡片未列任何 GPU／VRAM 硬體需求** |
| 6 | [huggingface.co/Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | 官方 | 完整 | Text-Only 選項 `--language-model-only` 可跳過視覺編碼器以釋出 KV cache 記憶體；BF16 safetensors 19,306,390,537 bytes（約 19.3GB）；vLLM／SGLang 需 main 分支；工具呼叫敘述與 `--tool-call-parser qwen3_coder` |
| 7 | [HF collection qwen38](https://huggingface.co/collections/Qwen/qwen38)、[Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)、[Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) 模型卡 | 官方 | 第一輪（2026-10-03）完整；本輪未重抓 | 沿用第一輪結果（見 1.4 表） |

失敗／限制連結（沿用第一輪記錄）：`qwen.ai/blog` 為 JS 動態頁，工具抓不到內文；舊官方 blog `qwenlm.github.io/blog` 最後文章 2025-09-23 後停更。2026 年公告以 GitHub README 與 HF 模型卡為準。

### 1.3 「Qwen 3.8」核實結論（F09 修訂）

**修訂後結論：Qwen3.8 是官方系列（2026-08），最小開源檢查點為 27B dense。其官方 BF16（約 55.6GB、18 分片）與官方 FP8（約 30.9GB／≈28.7GiB）確實超過單卡 24GB、無法全放；但 27B GGUF 4-bit（實作者 Unsloth 資料：需求 16–19GB；工件 UD-Q4_K_M 16.5GB／UD-Q4_K_XL 17.6GB）是值得 3090 實機測試的候選，尚未實測。使用者的 Qwen3.8 候選不被排除。**

原結論與修訂對照：

| 面向 | 原結論（第一輪） | 修訂結論（F09 輪） |
| --- | --- | --- |
| Qwen3.8 是否官方系列 | 是（僅 2.4T-A95B 與 27B 兩檢查點） | 不變（本輪重讀 repo 確認） |
| 27B 官方 BF16 | 約 55.5GB > 24GB | 不變；本輪實際讀得 55.6GB（55,563,118,992 bytes） |
| 27B 官方 FP8 | 約 28GB > 24GB | 不變；本輪實際讀得 30.9GB（≈28.7GiB）；且卡片未列硬體需求，「FP8 可行」說法以檔案大小即否 |
| 27B 在 3090 的整體判定 | 「無法直接在 RTX 3090 上以官方檢查點執行」，並載明「不列入 3090 首選」——被讀成「Qwen3.8 跑不動 3090」 | **過度概括，修訂：官方檢查點無法全放 24GB；27B GGUF 4-bit（實作者資料 16–19GB）是值得 3090 實機測試的候選，尚未實測** |
| 使用者 Qwen3.8 候選 | 「不列入首選，除非使用者接受社群 INT4 並另行驗證」 | **不排除；因使用者指定此系列，列為優先實測對象（見 1.6）** |
| llama.cpp／GGUF 路線 | 僅註記「實際檔案為社群量化」 | 官方 repo Local Use 段明列 llama.cpp 並連結 Unsloth 指南——GGUF 路線有官方指引；但量化檔本身仍是實作者（Unsloth）工件，非 Qwen 官方權重 |
| NVFP4 | 未提 | Unsloth 頁明示 NVFP4 需 Blackwell（RTX 50X、DGX Spark、B200、B300）；3090 為 Ampere，NVFP4 的速度與顯存數字**不可套用**；3090 量化路線以 GGUF 為主 |
| Qwen3.5-9B「24GB 可跑」 | 直接寫「24GB 可跑（BF16 約 19.3GB，緊）」 | 收斂為：19.3GB 是權重檔大小，**不等於已能運行**——KV cache、視覺編碼器與框架開銷使完整峰值顯存未量測前不能定論；模型卡提供 `--language-model-only` 跳過視覺編碼器釋出 KV cache，是待驗證的緩解選項 |

分類證據明細：

**官方證據**（QwenLM GitHub／HF Qwen org，2026-10-03 完整讀取）：

- QwenLM/Qwen3.8 README：Local Use 段列 Transformers、**llama.cpp**（「Look for models ending with GGUF on Hugging Face Hub」）、MLX、Unsloth，並以「the Qwen3.8 guide」連至 `unsloth.ai/docs/models/qwen3.8`。
- Qwen/Qwen3.8-27B 模型卡：BF16 約 55.6GB（18 分片）、262,144 native context、`<tool_call>` chat template、Apache-2.0、附「Browse Quantizations」連結（內容為社群量化）。
- Qwen/Qwen3.8-27B-FP8 模型卡：約 30.9GB、F8_E4M3 block 128；未列硬體需求。
- Qwen/Qwen3.5-9B 模型卡：`--language-model-only`（Text-Only）跳過視覺編碼器以釋出 KV cache；BF16 約 19.3GB。

**實作者證據**（Unsloth，非 Qwen 官方權重，2026-10-03 完整讀取）：

- 指南：27B 4-bit 需求 16–19GB；「For older GPUs, our GGUFs work well!」（未點名 3090）；NVFP4 需 Blackwell；MTP 另需 1–2GB。
- GGUF 工件：UD-Q4_K_M 16.5GB、UD-Q4_K_XL 17.6GB、mmproj 視覺檔另計；Apache-2.0；`llama serve` 示範指令；架構 `qwen35` 需較新 llama.cpp。

**未驗證／待實測項**：16–19GB 估計未在本機或 3090 實測；GGUF 4-bit 下中文理解與工具呼叫正確率未知；3090 對官方 FP8 的硬體支援未查（FP8 檔案本身已超卡，此問題僅備忘，不影響結論）。

「Qwen 3.8」的可能原意與對應（供使用者確認，不暗自換型號）：

1. 指 **Qwen3.8 系列**：官方存在；3090 路線為 27B GGUF 4-bit（實作者量化），已列為優先實測對象，實測前不定論。
2. 指「Qwen3 的 8B」即 **Qwen3-8B**：官方存在（2025-04-27，Apache-2.0），BF16 約 16.4GB 可為候選。
3. 指約 8B 級的最新官方模型：即 **Qwen3.5-9B**（2026-03-02，Apache-2.0），權重約 19.3GB 在 24GB 內但緊，需完整峰值量測。

### 1.4 候選清單（F09 修訂擴充；全部標 3090 實測 HOLD）

每個候選標明「官方權重 vs 社群量化」。顯存數字除標明來源者外均為推算或檔案大小，非官方 VRAM 需求，更非實測。

| # | 候選 | 官方權重或社群量化 | 檔案／權重大小 | 顯存估計（類別） | Context | 工具呼叫證據 | 3090 判定 | 實測優先序 | 來源 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Qwen3.8-27B GGUF Q4_K_M（unsloth UD-Q4_K_M）** | **社群量化（Unsloth）**；基底 Qwen/Qwen3.8-27B 為官方 Apache-2.0 | 16.5GB（UD-Q4_K_XL 17.6GB 為 Unsloth 建議 4-bit 變體，備選） | 16–19GB（**實作者資料**：Unsloth 指南；未實測） | 原生 262,144（實際以 llama.cpp 設定為準） | 基底模型卡 `<tool_call>` 模板與 agentic 基準；llama.cpp 下正確率待實測 | **候選，值得實機測試；未實測** | **1（使用者指定系列）** | [官方 repo](https://github.com/QwenLM/Qwen3.8)｜[Unsloth 指南](https://unsloth.ai/docs/models/qwen3.8)｜[GGUF 工件](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF)｜[基底模型卡](https://huggingface.co/Qwen/Qwen3.8-27B) |
| 2 | Qwen3.5-9B | 官方權重（BF16）；另有非官方 FP8／GGUF 社群量化 | BF16 safetensors 約 19.3GB | 權重 19.3GB＋KV 另計（**官方檔案大小＋推算**；`--language-model-only` 可略過視覺編碼器釋出 KV，待驗證） | 262,144（YaRN 至 1,010,000） | 模型卡明文「excels in tool calling」＋Qwen-Agent／MCP＋`--tool-call-parser qwen3_coder` | 權重可入但緊；**完整峰值未量，不定論** | 2（官方權重直跑之對照組） | [HF 模型卡](https://huggingface.co/Qwen/Qwen3.5-9B) |
| 3 | Qwen3.5-4B | 官方權重（BF16）；另有社群量化 | 約 9.3GB | 約 9.3GB＋KV（**推算**；寬裕） | 262,144（YaRN 至 1,010,000） | 同系列模型卡工具呼叫敘述 | 可行待實測 | 3（顯存寬裕之降級退路） | [HF 模型卡](https://huggingface.co/Qwen/Qwen3.5-4B)（第一輪完整讀取） |
| 4 | Qwen3-8B | 官方權重（BF16）；另有大量社群量化 | 約 16.4GB | 約 16.4GB＋KV（**推算**） | 32,768（YaRN 131,072） | 模型卡明文 agent 能力；vLLM tool parser 與 Qwen-Agent 文件最齊 | 可行待實測 | 4（純文字、生態成熟之框架退路） | [HF 模型卡](https://huggingface.co/Qwen/Qwen3-8B)（第一輪完整讀取） |
| 參照 | Qwen3.8-27B（官方 BF16／官方 FP8） | 官方權重 | BF16 約 55.6GB／FP8 約 30.9GB（≈28.7GiB） | — | 262,144（YaRN 至 1M） | 同候選 1 | **超過 24GB，不排單卡全放；不列實測** | — | [模型卡](https://huggingface.co/Qwen/Qwen3.8-27B)｜[FP8 卡](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) |

**NVFP4 不適用 3090**：Unsloth 指南明示 NVFP4 需 Blackwell（RTX 50X、DGX Spark、B200、B300），其宣稱速度（約 1.5× BF16）與顯存數字僅在該架構成立；RTX 3090 為 Ampere，不可套用。3090 的量化路線以 GGUF 為主（同頁「For older GPUs, our GGUFs work well!」，實作者資料）。

更小的官方同系列檢查點（低於 4B，備查）：Qwen3.5-2B、Qwen3.5-0.8B（2026-03-02，GitHub README 列出）。

已排除（單卡 24GB 不可行或授權不符）：

- Qwen3.8-2.4T-A95B／-FP8：2.4T 總參 MoE 旗艦，總權重遠超 24GB。
- Qwen3.8-Flash-Next：約 180B 總參 MoE 預覽，且授權 `qwen-community-1.0` 非 Apache 2.0。
- Qwen3.5-397B-A17B、Qwen3.5-122B-A10B、Qwen3.5-35B-A3B、Qwen3.6-35B-A3B、Qwen3-Coder-30B-A3B：MoE 總參數量使 BF16／FP8 權重皆超 24GB。
- Qwen3.5-27B、Qwen3.6-27B：dense 27B 官方權重超卡；若未來比照 GGUF 路線另議，非本輪範圍。

### 1.5 官方推薦推論框架與工具呼叫文檔位置

| 框架 | 官方支援狀態與文檔位置（F09 輪補強） |
| --- | --- |
| vLLM | [QwenLM/Qwen3.8 README](https://github.com/QwenLM/Qwen3.8) serving 段：`vllm serve "Qwen/Qwen3.8-27B"`，工具呼叫用 `--tool-call-parser qwen3_coder --enable-auto-tool-choice`。Qwen3.5-9B 卡：生產建議 vLLM（需 main 分支版本）＋`--language-model-only`（Text-Only）。Qwen3-8B 卡：vLLM ≥ 0.8.5 |
| SGLang | 同上 README 列為生產建議；Qwen3.5-9B 卡同列（需 main 分支） |
| llama.cpp | **F09 補強：官方 repo Local Use 段明列 llama.cpp（「Look for models ending with GGUF on Hugging Face Hub」）並連結 Unsloth Qwen3.8 指南**——GGUF 路線有官方指引。但官方模型卡僅為 BF16 safetensors（`isQuantized: false`），實際 GGUF 檔為社群量化（unsloth 等）；GGUF 工件頁標示架構 `qwen35`，需較新 llama.cpp；工具呼叫行為待實測 |
| Ollama | 官方 README 未列為建議框架；僅在 llama.cpp／Ollama／LM Studio 相容之社群量化說明中出現 |
| transformers | Qwen3-8B 卡要求 ≥ 4.51.0；Qwen3.5-9B／Qwen3.8-27B 卡列直接載入方式（Qwen3.5 需 main） |
| Qwen-Agent | Qwen3.5 與 Qwen3 模型卡建議的官方 agent 框架（含 MCP 支援） |

### 1.6 實測優先順序與理由（F09 修訂，取代原「建議首選」）

修訂說明：原第 1 條「首選候選：Qwen3.5-9B」與第 4 條「Qwen3.8-27B 不列入 3090 首選」的寫法，效果上把使用者指定的 Qwen3.8 系列排除在外。修訂後**不是排除 Qwen3.8，而是列出實測優先順序與理由**；最終型號由 3090 實測結果＋使用者確認決定，不預先鎖定。

1. **優先實測對象一：Qwen3.8-27B GGUF UD-Q4_K_M（16.5GB），備選 UD-Q4_K_XL（17.6GB）**。理由：這是使用者指定的 Qwen3.8 系列；官方 repo 明列 llama.cpp 路線；實作者資料估 4-bit 16–19GB 在 24GB 內。以 llama.cpp 實測峰值 VRAM、載入、延遲、context 與工具呼叫正確率；未實測前不定論可行或不可行。
2. **優先實測對象二：Qwen3.5-9B（官方 BF16）**。理由：不需依賴社群量化即可直跑、最接近 8B 級的最新官方中型模型；作為 Qwen3.8 GGUF 的對照組。`--language-model-only` 跳過視覺編碼器釋出 KV cache 是官方提供的緩解選項；19.3GB 權重不等於已能運行，須完整峰值量測。
3. **其後：Qwen3.5-4B（顯存寬裕、延遲更低）、Qwen3-8B（純文字、工具呼叫生態最成熟）**：作為前兩者實測失敗或不足時的降級／退路。
4. **不在 3090 測**：NVFP4（Blackwell only）；Qwen3.8-27B 官方 BF16／FP8（檔案超 24GB）。
5. 所有候選在 SERVER（OS／CUDA 未知）依第二部分計畫實測後，連同結果回報使用者鎖定；`configs/agent_model.yaml` 的 `default_candidate` 維持 null，不擅自鎖定。

---

## 二、3090 實測（HOLD：待 SERVER）

**狀態：HOLD——依 `docs/SERVER_INVENTORY.md`，SERVER OS、位址、CUDA／驅動版本未取得，以下全部為計畫，尚未執行、無任何數值。**

### 2.1 T25 實測計畫表

| 欄位 | 計畫內容 |
| --- | --- |
| 模型與 revision hash | 實測下載時記錄：`unsloth/Qwen3.8-27B-GGUF` 與基底 `Qwen/Qwen3.8-27B`（及 Qwen3.5-9B 等官方候選）的 commit hash（HF 頁面／API 取得）。本輪頁面未顯示 revision，不預填、不虛構 |
| 量化檔與大小 | GGUF 首選 `UD-Q4_K_M.gguf`（16.5GB）、備選 `UD-Q4_K_XL.gguf`（17.6GB）；mmproj 視覺檔是否載入另記（純文字代理人可先不載）。官方候選記 BF16 檔案大小與分片 |
| 框架與版本候選 | GGUF → **llama.cpp**（需支援 `qwen35` 架構之較新版本；記錄 build／commit 版本號）。官方 BF16 → **vLLM**（Qwen3.5 需 main 分支；記錄版本號；`--tool-call-parser qwen3_coder --enable-auto-tool-choice`；Qwen3.5-9B 加 `--language-model-only`）。SGLang 備查（記版本）。transformers 僅除錯用 |
| context 上限設定 | 分段測 8K → 16K → 32K，記錄各段 KV 佔用與峰值 VRAM；以本案實際需求（少量中文文字＋結構化工具參數）為準截斷，不用滿 262K |
| 併發 | 1（單一代理人互動情境）；併發 >1 的行為另行記錄，不預設支援 |
| 測試案例 | (a) 中文菜名別名抽取：甘藍＝高麗菜、空心菜、小白菜等；規格（顆／半顆／斤）；單位（元/臺斤 vs 元/公斤）。(b) 工具參數生成：對 `POST /forecast` 生成正確 JSON（品項、今天價、選填上週價與日期、7／14 天）。(c) 不相關輸入的拒答或降級行為 |
| 量測項 | 峰值 VRAM（nvidia-smi，載入後與推論中，含 KV）、載入／啟動時間、首 token 延遲、生成速度（tokens/s）、完整回應時間 |
| 環境記錄 | OS／驅動／CUDA／框架與 llama.cpp 版本全部記錄；NVFP4 不測（Blackwell only，3090 不適用） |

### 2.2 待測項目結果欄（取得 SERVER 後填入，證據放 `outputs/server/qwen_benchmark/`）

| 項目 | 內容 | 結果 |
| --- | --- | --- |
| 環境 | OS／驅動／CUDA／框架版本 | 未測 |
| 載入 | 各候選實際載入成功與否、啟動時間 | 未測 |
| 峰值顯存 | 載入後與推論中 `nvidia-smi` 峰值（含 KV cache 設定） | 未測 |
| 延遲 | 首 token 與完整回應時間（中文菜價查詢句） | 未測 |
| 有限 context | 8K／16K／32K 設定下行為與 KV 佔用 | 未測 |
| 併發 1 行為 | 單一代理人連續請求的穩定性與資源回收 | 未測 |
| 中文品項理解 | 菜名／別名／規格／單位抽取正確率（甘藍＝高麗菜、空心菜、元/臺斤等） | 未測 |
| 工具參數正確率 | 對 `POST /forecast` 等工具的 JSON 參數生成正確率 | 未測 |
| 並存 | 與菜價模型推論服務同卡的顯存分配 | 未測 |

驗收門檻（依 TASKS T25）：真權重載入與實際請求輸出（版本、量化、顯存、延遲、工具案例）才可標 PASS；僅官方頁可讀不算實測通過。

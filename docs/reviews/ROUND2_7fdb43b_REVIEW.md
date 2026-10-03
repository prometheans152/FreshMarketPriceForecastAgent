# 第二輪獨立審查：7fdb43b

審查日期：2026-10-04。結論：**需要修改；不能依「98 項測試全綠」放行第二輪本機代理人／更新流程。**

審查對象為提交 `7fdb43b` 與使用者貼上的 GLM 回報。主審實讀程式、任務契約、輸出與畫面，另委派兩位唯讀審查者分別核對代理人/API及資料/模型/更新。沒有修改實作、重新選模、重訓或部署。

## 已確認的成果與證據界線

- 主審重跑 `.venv/Scripts/python.exe -m pytest -q`，結果 **98 passed、6332 warnings、8.66 秒**。這證明目前套件中的測試通過，不代表全部自然語言情境、真正 Qwen、3090 或外網手機已驗收。
- 本機流程確實呼叫 `ForecastEngine.forecast()`，不是把菜價模型結果寫死在模板；規則回答也確實引用模型輸出。
- 已查看 `outputs/e2e/ui_agent_mobile.png`，畫面有規則模式、7/14 天與 B 實驗性說明。這是本機瀏覽器手機尺寸畫面，不能證明真正手機在蔬果行連上 SERVER。
- 獨立審查者從既存逐列 `test_predictions.csv` 重算 MAE/macro-F1及標籤、7/14天日期差，與 JSON 相符；沒有重新訓練或使用測試集選型。
- 主審重現紀錄：[review_reproductions.json](../../outputs/audits/2026-10-04_round2/review_reproductions.json)；可重跑的唯讀檢查：[reproduce_review.py](../../outputs/audits/2026-10-04_round2/reproduce_review.py)。其中 Qwen 回傳與資料下載部分使用模擬傳輸，檢查的是應用程式處理路徑，不是 Qwen 品質或官方新行情。
- 正式 `models/releases/0.1.0/` 五個檔案在主審缺陷重現前後 hash 相同；原始逐字稿 SHA256 仍為 `46b80ee649fcc11dfd7a1a8d5ea134a148883242767cd43b27d5d1e1587d4d3f`。

## 需修正的發現

### F01｜P1：解析器把不同單位、日期與店家合併為可比價格

位置：[tools.py](../../src/aiot_price/agent/tools.py) 第49、85、113–149行；[predict.py](../../src/aiot_price/models/predict.py) 第197–202行；[store_adapter.py](../../src/aiot_price/models/store_adapter.py) 第46–57行。

主審固定今天為2026-10-04，重現結果如下：

| 輸入 | 實際行為 | 問題 |
| --- | --- | --- |
| 高麗菜今天一斤32元，上週一公斤50元 | 今天32元/公斤、上週50元/公斤 | 全句先選公斤，再複製給兩個價格；今天應為32元/台斤。正確的兩筆同口徑價格是32及30元/台斤。 |
| 高麗菜昨天一斤32元 | 建立今天2026-10-04的報價 | 把明示昨天改成今天。 |
| 高麗菜今天一斤32元，上次一斤28元 | 自動建立2026-09-27上週價 | 「上次」沒有提供日期，程式自行補七天前。 |
| 高麗菜今天一斤32元，上週2026-09-01一斤28元 | 忽略明示日期，仍填2026-09-27 | 繞過7±2天可比性檢查。 |
| 高麗菜今天一斤32元，上週另一家店一斤28元 | 執行B | 把不同店家價格當同店近期變化。 |

獨立審查者另重現「高麗菜一顆30元，青江菜一斤45元」被接受為高麗菜30元/台斤。多商品、不同規格與不同單位必須分別綁定價格，歧義或不支持時要求補充，不能只取第一個菜名／價格與整句第一個單位。

`check_b_input()` 雖有規格一致旗標，推論入口沒有接入；目前靠預設True，不能把函式的單元測試當成換規格已在API處理。需要完成端到端可比性與日期驗證。

### F02｜P1：Qwen安全提示未載入，矛盾回答直接通過

位置：[service.py](../../src/aiot_price/agent/service.py) 第19–25、105–135行；[test_faithfulness.py](../../tests/agent/test_faithfulness.py) 第49–57行。

`parents[2]` 指向 `src/`，實際讀取 `src/configs/agent_prompt.md`。正確檔案在專案根目錄。主審實讀：預設路徑不存在、提示長度為 **0**，缺檔還默默回空字串。

即使修正路徑，程式也會直接回傳模型文字，沒有把方向、數字、機率與同店聲明對照工具真值。主審模擬Qwen回傳「7天後必定上漲99%，售價999元；這是已驗證的同店結果」，應用程式原樣接受。這不是聲稱真正Qwen已說出該句，而是證實輸出防線缺失。

現有名為核對方向／數字的測試實際只檢查文字含「7天後／14天後」。應逐項比較工具真值；提示不能代替輸出驗證。前端應保留獨立的結構化預測結果，解釋錯誤時仍呈現正確工具結果與真實降級狀態。

### F03｜P1：Qwen等待阻塞其他API請求

位置：[app.py](../../src/aiot_price/api/app.py) 第159–187行；[service.py](../../src/aiot_price/agent/service.py) 第92、133行。

非同步路由直接執行同步流程，Qwen又使用同步網路讀取，預設等待30秒。獨立審查者使用延遲0.5秒的模擬後端發併發請求：health在約0.021秒開始，直到約0.764秒與agent一起完成。

應使用受控執行緒或非同步I/O，避免一個Qwen請求影響其他健康／菜價查詢；補入併發與超時降級的行為驗證。這是本機可修問題。

### F04｜P1：正常下載新行情的更新路徑會中斷

位置：[update_public_data.py](../../scripts/update_public_data.py) 第415、432行。

非dry-run下載有新資料時，先把`candidate.json`搬到快照目錄，之後仍使用已不存在的原路徑刷新歷史。主審以模擬HTTP200的新日期資料，執行完整`main()`且只寫系統暫存副本，結果為：新快照已保存 → `FileNotFoundError` → 沒有報告 → 歷史未追加。

原b2情境使用`--input`，走複製而非搬移路徑，不能覆蓋正常下載後的路徑。必須增加「download＋有新日期＋非dry-run＋refresh」整條路徑驗證，且所有失敗要回受控狀態與報告。

### F05｜P2：更新的保護、schema與生效驗證仍不完整

位置：[update_public_data.py](../../scripts/update_public_data.py) 第88–126、258–279、367行；[update_policy.yaml](../../configs/update_policy.yaml) 第42、65行；[predict.py](../../src/aiot_price/models/predict.py) 第54、138、190行；[app.py](../../src/aiot_price/api/app.py) 第69–73行。

- **損毀保護：** 直接覆寫目標parquet，沒有校驗完成後原子替換／例外恢復。主審在副本模擬寫入中斷：目標剩下`partial parquet`，備份存在但沒有還原。策略寫「以備份還原」尚未實作。寫入或核對失敗都必須保留可用舊檔。
- **欄位／值：** 主審移除甘藍欄，schema仍回`errors=[]`。獨立審查另確認`Infinity`能進入歷史，以及壞JSON未回受控schema錯誤。至少驗證每列必要欄位、三個支援品項、有效日期、有限價格與鍵唯一性；正常的0仍依契約處理缺測。
- **生效：** 行情只在引擎初始化時載入，API長期快取該實例。更新磁碟不會讓既有服務自動看到新行情。需要明確且實測的安全重載／重啟步驟。
- **資料日期：** 全域快照截止不是特定市場／品項實際使用的最新價格日。例如10/2 fixture特徵只用到10/1，但解釋寫「最新可見10/2」。分開記錄快照截止、特徵可見日期、價格年齡與更新資料版本。

### F06｜P2：8KB限制可繞過，錯誤上週日期回500

位置：[app.py](../../src/aiot_price/api/app.py) 第44–49行；[predict.py](../../src/aiot_price/models/predict.py) 第197–202行。

主審用沒有Content-Length的chunked合法JSON請求，本文 **9,198 bytes**，`/forecast`仍回200與兩筆預測。限制目前只相信標頭，沒有在讀取時限制實際位元組數。

`previous_observed_at="not-a-date"`則回 **HTTP500**，應回受控輸入錯誤或有理由的A降級。另需按共用契約檢查有限數字、日期時區與匿名店號，不能把JSON schema文件存在當作API實際執行了驗證。

### F07｜P2：代理人店號與降級標示錯誤

位置：[app.js](../../web/app.js) 第61、135–143、489、501–508行；[service.py](../../src/aiot_price/agent/service.py) 第135–138、175–189行。

表單保存店號至`tw01_ui_prefs_v1`的JSON，代理人卻讀`vp_store_id`，因此使用者改店號後仍可能傳`store-a`。應使用目前表單／同一套選項來源並驗證。

Qwen失敗降級時仍回`backend=qwen`，手機標成「Qwen代理人」。主審模擬超時，確認規則回答有真模型數字，但backend仍為qwen。應回實際執行的後端與降級原因；目前也沒有獨立forecast物件供前端結果卡顯示。

### F08｜P2：T26與T22整項PASS缺少驗收

位置：[TASKS.md](../../TASKS.md) 第264–272、305–314行；[service.py](../../src/aiot_price/agent/service.py) 第105–124行；[prediction_records.py](../../src/aiot_price/api/prediction_records.py) 第19行；[design.md](../../design.md) 第83、149行。

T26本機規則流程是實作成果，但Qwen僅取得已執行工具的JSON做解釋，請求沒有tools schema／tool_calls／工具迴圈；T24/T25與SERVER追蹤也未通過。與既定「Qwen理解、呼叫工具與解釋」的設計有差異。**T26整項應DOING，分別記錄本機與SERVER證據**，不要求老師未明確規定的額外能力。

T22目前找到保存／讀取／匯出函式與測試，沒有找到手機/API的保存、匯出及刪除入口。這只能證明函式層，未滿足一般使用者選擇保存並於到期核對的完整流程；補接入並驗收，或修正狀態為部分完成。

有上述缺陷的T14/T19/T20/T21等相關任務也須依修正後的證據重驗，不能只把T26的PASS減一就宣稱其餘PASS全部獨立審過。

### F09｜P2：Qwen3.8「跑不動3090」過度概括

位置：[QWEN_SERVER_BENCHMARK.md](../QWEN_SERVER_BENCHMARK.md) 第23–47、84–88行；[agent_model.yaml](../../configs/agent_model.yaml)；D38及使用者收到的回報。

2026-10-04重新查官方／實作者來源：

1. [Qwen官方repository](https://github.com/QwenLM/Qwen3.8)確認Qwen3.8-27B存在，Local Use段明列llama.cpp，並直接連到Unsloth量化指南。
2. [Unsloth實作者指南](https://unsloth.ai/docs/models/qwen3.8)列27B的4-bit量化需求約16–19GB，提供[GGUF工件](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF)，並說明較舊GPU可使用GGUF。
3. NVFP4另要求Blackwell，不可把其速度／顯存數字直接套到Ampere的3090。
4. [Qwen3.5-9B官方模型卡](https://huggingface.co/Qwen/Qwen3.5-9B)說明可略過視覺編碼器以釋出KV cache記憶體，沒有保證只看權重檔大小就能在所有24GB設定運作。

因此合理結論是：**27B未量化BF16／官方FP8不適合全放24GB；27B GGUF 4-bit是值得測試的3090候選，尚未實測；9B也需量測完整推論顯存與延遲。** 不應催使用者依「Qwen3.8跑不動」改選系列。保留使用者原候選與未定狀態，準備模型revision、量化檔、框架、有限context與工具案例；SERVER到位再做真正比較。量化指南是實作者資料，不能冒充Qwen自行發布的量化權重或本機測試。

### F10｜P2：重現依賴與狀態文件未同步

位置：[requirements-lock.txt](../../requirements-lock.txt) 第2行；[pyproject.toml](../../pyproject.toml) 第15–28行；[REPRODUCIBILITY.md](../REPRODUCIBILITY.md) 第33、83–84行；[README.md](../../README.md) 第5、17、20行；[PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) 第14行；[TASKS.md](../../TASKS.md) 第36行。

- lock仍有目前電腦的絕對editable路徑。換checkout或SERVER會指向錯誤／不存在的位置，應改可攜形式並在另一目錄乾淨環境驗證。
- `pyproject.toml`尚缺API及parquet所需的FastAPI、Uvicorn、PyArrow等依賴；標準開發安裝與後續API/管線步驟不相符。
- 重現文件仍說lock沒有FastAPI，但lock已經有；列出的部分基線預期數字也與JSON不符。
- README仍有63tests、全TODO、尚無訓練等混合狀態，背景仍寫只準備文件，TASKS開頭稱36項全TODO，與個別任務及提交矛盾。

整合實際修正結果後同步文件，不要只補一份回報而讓接手入口保持舊狀態。

## 模型成果的實際解讀

| 項目 | 7天 | 14天 |
| --- | --- | --- |
| 選定模型macro-F1 | 0.4218 | 0.4169 |
| momentum簡單趨勢macro-F1 | 0.4226 | 0.4306 |
| 選定模型變化率MAE | 0.0664 | 0.0983 |
| 不變價基線變化率MAE | 0.0436 | 0.0748 |
| 公開測試上漲召回率 | 約10% | 約9% |

選定模型沒有勝過簡單趨勢基線，點誤差也未勝過不變價。報告如實並列屬正確做法；不能宣稱已證明预测更準。MAE是相對變化率，不是元。上漲召回低也直接限制「下週會不會漲」的用途，應保持公開模型原型定位。

模型選型原先在驗證集凍結；不能看過測試後挑momentum或重調模型，仍沿用原封存測試當新的獨立證明。之後要改方法，須規劃新的未見期間／前瞻驗證。B仍是固定係數實驗性規則，沒有同店效果證據；T16繼續HOLD。

## 後續處理

先修本機F01–F08及F10，補能抓到上述錯誤的行為測試；F09先修研究結論與候選計畫，不需要立刻下載大型權重或選新模型。Qwen實機、跨主機部署、外網手機、真店到期價與正式交付各自保持待驗證。下一輪完整工作提示：[GLM_ROUND3_REPAIR_PROMPT.md](../GLM_ROUND3_REPAIR_PROMPT.md)。

這次審查沒有重新確認當屆Notion期末公告，也沒有完成T36全部交付驗收；老師資料沒有明確要求的性能門檻，不因本次程式問題自行追加。

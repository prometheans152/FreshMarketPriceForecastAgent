# U01–U50 獨立覆核結果（G清單依據）

覆核日期：2026-10-03。本輪以五個查核代理＋主對話覆抽，對U清單47題（34題全項覆核、6題主來源親驗、7題資料集經兄弟題驗證＋前作連結抽查）重新實測資料頁、下載端點與關鍵欄位，並另查前作。本檔是G清單（[GENERAL50_TOPIC_CATALOG](../GENERAL50_TOPIC_CATALOG.md)）中U派生題的證據基礎。

## 覆核等級定義

- **全項覆核**：代理實測資料頁＋（可行時）樣本＋另查前作，判定證實／部分證實。
- **主來源親驗**：主對話curl實測主要資料端點（HTTP狀態、檔案大小、欄位），前作沿用原卡標示。
- **兄弟題驗證**：該題所用資料集已由同來源兄弟題全項覆核，前作連結經抽查存活；任務級差異設計沿用原卡，未逐項重驗。

## 判定總表

| U題 | G編號 | 等級 | 判定 | 本輪新證據／勘誤 |
| --- | --- | --- | --- | --- |
| U01 | G05 | 全項 | 證實 | TFDA CSV下載HTTP 200、3,050,521 bytes與原卡逐位元組一致；營養小幫手App存在證實「查詢介面即淘汰」前提。 |
| U02 | G06 | 全項 | 證實（前作壓力上修） | 匯出976,647 bytes一致、首筆己二烯酸樣本已讀；FoodSense已覆蓋727種添加物解讀＋個人化掃描，差異僅剩複方嵌套解析。 |
| U03 | G07 | 主來源親驗 | 證實 | InfoId=199 JSON HTTP 200（301後跟隨）、70,860 bytes、欄位成分名/INCI名/CAS_NO.等與原卡一致。 |
| U04 | G49 | 全項 | 證實（補強） | publications.json整檔118,238筆（原卡未確認總數）；ISBN覆蓋61.6%；PublishDate含1912-01至2027-03未來日期，佐證「不作版次真值」。 |
| U05 | G11 | 全項 | 證實 | symbols.json 9,314 bytes、31項、MIT、2026-09-23仍在更新；消保處PDF 200。 |
| U06 | G12 | 全項 | 證實 | 3001.dat 663 bytes實讀（CC BY 4.0檔頭）；LDraw授權頁（CC BY 4.0＋CC0選項）實讀。 |
| U08 | G21 | 主來源親驗 | 證實 | Chesscog repo MIT、2025-01仍在維護；OSF DOI 302正常解析。原卡OSF val.zip 206區域取樣與JSON樣本屬前次紀錄。 |
| U09 | G20 | 全項 | 證實 | Lichess題庫CC0、更新至2026-10-03、6,157,341題；欄位比原卡多DailyDate；HF快照877MB相符。 |
| U10 | G08 | 全項 | 證實（欄位勘誤） | TaiwanVQA 2,736張全自攝＋5,472人工問答、CC BY-SA 4.0、parquet可下載；**HF欄位清單無`data_source`，原卡此欄位名有誤**。 |
| U12 | G22 | 全項 | 證實 | DRCD GitHub CC BY-SA 3.0；training JSON串流首900 bytes實讀（version 1.3、首條廣州條目）。 |
| U13 | G23 | 兄弟題驗證 | 資料證實 | DRCD資料集同G22已驗；前作QAGS、AlignScore連結本輪抽查HTTP 200。 |
| U14 | G24 | 兄弟題驗證 | 資料證實 | DRCD同上；前作pd3f/dehyphen連結抽查200。整合查核已確認此卡以DRCD＋明示合成斷行（CC BY-SA 3.0）。 |
| U15 | G26 | 全項 | 證實 | Mozhub cc0-sentences CC0；chatlogs.txt位元組級UTF-8解碼實讀台灣日常口語句；26,393句與README一致。 |
| U16 | G27 | 兄弟題驣證 | 資料證實 | 同一MozTW倉庫已驗（CC0、21檔）；Windows/Gmail/PhraseExpress自動完成前作連結存活。 |
| U18 | G28 | 全項 | 證實（前作勘誤） | CLDR release-48 zh_Hant.xml實讀3,932個annotation（1,966 tts）、Unicode-3.0；**原卡SwiftKey連結現404**，功能屬實需換連結；新前作arXiv:2409.10760（多正例emoji推薦）應引用。 |
| U19 | G29 | 全項 | 證實 | HF鏡像API實測gated:false、CC0；train 7,394/validated 85,324；**首筆實讀含`duration_ms=3708`**——語速可直接計算，關鍵疑點解除。 |
| U21 | G30 | 兄弟題驗證 | 資料證實 | CV zh-TW同G29已驗；Audacity truncate-silence手冊與whisperX連結抽查200。 |
| U22 | G31 | 全項 | 證實 | InQSS repo實讀：TMHINT-QI免申請下載、raw_data.csv含quality/intelligibility分數欄、4筆缺值檔名與原卡相符；ISCA論文頁確認「首個中文語音品質＋可懂度資料集」。 |
| U23 | G32 | 兄弟題驗證 | 資料證實 | TMHINT-QI同G31已驗；arXiv:2309.12766與ACL 2026 findings連結抽查200。 |
| U24 | G33 | 全項 | 證實 | WiC zip記憶體實讀：train 5,428/dev 638/test 1,400與原卡逐字一致、標籤均衡。 |
| U25 | G35 | 全項 | 證實 | Kaggle均一API version 9、CC BY-NC-SA 4.0、16,217,311筆；**免登入下載端點HTTP 206親測**（ZIP含Log_Problem.csv）；欄位total_sec_taken/is_correct等經實用repo核對存在。 |
| U26 | G37 | 全項 | 證實（計數微差） | v0.94.0 resw實讀1,587個data元素（原卡1,583，計法差異）；官方settings-search與Command Palette前作連結200。 |
| U27 | G38 | 主來源親驗 | 證實 | Aalto 136Mkeystrokes頁面HTTP 200、含dataset/download/license區塊；非商業署名授權沿用原卡。 |
| U28 | G50 | 全項 | 證實（管道變動） | 2020-12-18歷史快照CC BY-SA 4.0、LFS三檔HTTP 206可達、article_replies.csv欄位含userIdsha256實讀；**opendata現行master已改發布至HF `Cofacts/line-msg-fact-check-tw`（gated:auto）**——免登入僅對2020快照成立。 |
| U29 | G41 | 全項 | 證實 | 微資料真實來源為[data.gov.tw 94140](https://data.gov.tw/dataset/94140)（OGDL-1）；ZIP HEAD 9,351,851 bytes、Last-Modified 2026-04-27；觀光署官網只有PDF報告。微資料最新為113年（落後報告約一年）。 |
| U30 | G42 | 全項 | 證實 | 同94140（國內旅次檔）；運具選擇羅吉特前作已另查得（墾丁、日月潭案例）。 |
| U31 | G43 | 全項 | 證實 | 同94140；住宿類型選擇研究文獻多。 |
| U32 | G44 | 全項 | 證實 | 同94140；選地重視因素排序前作已查得。 |
| U33 | G45 | 全項 | 證實 | 同94140；活動特性分析（政大）＋POIBERT前作。 |
| U34 | G46 | 全項 | 證實（差異論述修正） | data.gov.tw 15856頁面與OGDL-1一致；XML 8,293,232 bytes與原卡逐位元組一致、7欄檔頭已讀；**北捷GOApp已有官方關鍵字比對＋符合通知**，差異須限定於「澄清式追問的學習排序」。 |
| U35 | G47 | 全項 | 證實 | 民航局準點率頁實測236期、最新115年8月（2026/09/29更新）；粒度為機場×月，無逐航班、取消不在分母。 |
| U36 | G48 | 全項 | 證實 | [TDCS M05A目錄](https://tisvcloud.freeway.gov.tw/history/TDCS/M05A/)免key免登入，1,895個日檔（最早2021-06-22）＋日期夾到前一日；data.gov.tw 37757 API授權1、頻率5分鐘。 |
| U37 | G09 | 兄弟題驗證 | 資料證實 | TaiwanVQA資料集同G08已驗（topic含地標類）；Google Photos地點分組前作連結存活；原卡已自記「真地標子集未讀」。 |
| U38 | G10 | 兄弟題驗證 | 資料證實 | TaiwanVQA同上；homebox/homebox-companion與arXiv:2406.09400連結抽查200。 |
| U39 | G40 | 全項 | 證實 | 故宮open data轉址digitalarchive.npm.gov.tw可讀；CC0低階（100萬畫素）約41萬幅＋中階CC BY 4.0；無官方批次API文件（IIIF可程式化取圖僅部分證實）；**descreening（摩爾紋）與掃描banding是不同退化**，主要對照應為SSCOR。 |
| U40 | G34 | 主來源親驗 | 證實 | HF API實測TaigiSpeech CC BY 4.0、gated:false、nan語言標籤；metadata.jsonl 1,600列/10語者與WAV規格屬前次紀錄。 |
| U41 | G19 | 全項 | 證實 | UCI 507頁：51人×18活動×3分鐘、CC BY 4.0、20Hz——與原卡相符；確認18類中無搭車/抖腿負例，原卡誠實標示正確。 |
| U42 | G16 | 全項 | 證實 | Zenodo 3371780：CC BY 4.0、hexaphonic六路、annotation.zip 39.1MB JAMS含string/fret positions——弦別標註存在；已知標註錯誤issue應列限制。 |
| U43 | G17 | 全項 | 證實 | MAESTRO V3.0.0：1,277檔、199.7小時、CC BY-NC-SA 4.0、MIDI對齊~3ms；Onsets and Frames前作確立。須固定引用V3。 |
| U44 | G13 | 主來源親驗 | 證實 | KiCad官方3D庫USB_Micro-B_Molex_47346-0001.wrl HTTP 200、315,050 bytes與原卡一致（CC BY-SA 4.0＋library exception）。 |
| U45 | G18 | 全項 | 證實（條件維持） | Zenodo 7672767影片CC BY 4.0、21支MP4共39.1GB、只含影片不含次數標註；S3主包1.7GB無授權標示；固定多視角機非手持——「深蹲影格/派生標籤待補」維持。 |
| U46 | G36 | 全項 | 部分證實 | 欄位組合（timestamp_TW＋同ucid＋未見upid＋提示/嘗試計數）支持派生標籤——但符合條件樣本數須下載3GB後計數，本輪未計數；MC-CPO（arXiv:2604.04251）確實用均一1,620萬互動且動機相同，前作壓力高。 |
| U47 | G14 | 全項 | 證實（補強） | iNat controlled_terms實讀（term 12 Flowers and Fruits四值）；台灣植物research grade＋雙CC 2020–2024四計數全數複驗（花8,421/果3,610/蕾1,767/無花果3,281）；**同條件總分母75,697→填寫率上限約22.6%**，「無註記即排除」紀律必須維持。 |
| U48 | G15 | 全項 | 證實 | 三物種台灣觀察數複驗（青葙136/紫茉莉19/含羞草141）；三筆樣本逐項吻合；公共照片為成熟株之限制屬實。 |
| U49 | G25 | 全項 | 證實 | DRCD 2,108條目/10,014段/30,000+問題；前作arXiv:2607.01018與卡描述完全相符；「human-in-the-loop確認流程」略強於可證內容，已註記。 |

## 未納入G清單的U題

| U題 | 處置 | 理由 |
| --- | --- | --- |
| U07 | 備案 | 資料（合成生成管線）可用，但DeckCheck App已做「攤開找缺牌」；差異只剩跨批同實體關聯且完全自建、未經測試，原卡自己也列撤回條件。 |
| U11 | 不重列 | 與G08/G09/G10同為TaiwanVQA第四個任務變體，本輆清單控制在每來源三題內。 |
| U17/U20 | 不重列 | 與G26/G27（MozTW）、G29/G30（Common Voice）同來源變體，控制每來源題數。 |

## 覆核工具與限制

- 五個代理共約180次工具呼叫；主對話覆抽12個關鍵端點（含U03/U08/U27/U40/U44/U50主來源與CWA颱風資料庫）。
- 本日WebSearch間歇限流：民間颱風假預測網站、CWA MOS校驗研究等前作未取得第一手連結，相關段落標未驗證；data.gov.tw搜尋頁500（全國A1/A2逐案集未補驗）。
- 「樣本已讀」均指本輪實際抓取；沿用原卡的前次實讀均已標注「前次紀錄」。未訓練任何模型、未採集家庭資料。

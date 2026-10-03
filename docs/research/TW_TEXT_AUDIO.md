# 台灣文字、語音與尋寵方向查核

查核日期：2026-10-03。只完成來源、實際樣本與既有作品比較；未訓練、未採集家庭資料、未登入或同意任何新的資料使用者條款。

## 保留 A1：家人台語指令的少量正負例校正

問題：家人各錄少量台語指令與容易混淆的閒聊後，在維持指令辨識率的條件下，能否降低非指令被接受的比例？最小成果限開燈／關燈的模擬結果。不是自動求助或實際家庭設備控制。

### 真實台灣訓練資料

- [TaigiSpeech 原作者公開資料](https://huggingface.co/datasets/TaigiSpeech/TaigiSpeech)：CC BY 4.0，台灣台語語音與意圖；不需登入或 API Key 即可下載本輪樣本。
- 本次直接讀取 [train metadata](https://huggingface.co/datasets/TaigiSpeech/TaigiSpeech/resolve/main/data/train/metadata.jsonl)、[val metadata](https://huggingface.co/datasets/TaigiSpeech/TaigiSpeech/resolve/main/data/val/metadata.jsonl)、[test metadata](https://huggingface.co/datasets/TaigiSpeech/TaigiSpeech/resolve/main/data/test/metadata.jsonl)：分別 HTTP 200，143,000／46,384／85,800 bytes，1,600／519／960 筆，共 3,079 筆。
- 真實欄位：`file_name`、`speaker_id`、`intent`。訓練／驗證／測試各有 10／5／6 位不同說話人；本次已讀三份說話人 ID 清單，沒有跨組重複。
- 八個真實標籤：SOS_CALL、FALL_HELP、BREATHING_CHEST_EMERG、PAIN_GENERAL、CALL_CONTACT、LIGHT_ON、LIGHT_OFF、CANCEL_ALERT。訓練每類 200，測試每類 120；不是完整家庭閒聊標籤。
- 實讀 [一段訓練 WAV](https://huggingface.co/datasets/TaigiSpeech/TaigiSpeech/resolve/main/data/train/audio/p001_0001_1_tw.wav)：683,358 bytes，單聲道、48,000 Hz、7.1175 秒。沒有下載整份音訊到工作區。
- 模型可用公開的 LIGHT_ON/OFF 起始訓練；其餘類別代表其他功能，不能說成一般聊天，更不能據此宣稱已有完整誤觸負例。資料標籤是語句意圖，不是實際疾病或事故真值。

### 實際既有作品與本題差異

| 已查作品 | 已完成的範圍 | 本題不能當新意的部分／另需驗證 |
| --- | --- | --- |
| [TaigiSpeech，2026 原文](https://arxiv.org/html/2603.21478v1) | 說話人分離的八意圖辨識、戲劇片段挖掘與適應；亦挖 OTHERS，做五類／二類緊急與非緊急分類。 | 台語智慧家庭、公開模型、非緊急分類均已做。未在本次已讀實驗見家人少量正負例校正前後、同一說話人的否定／轉述誤接受比較。 |
| [Google，Personalized Keyphrase Detection，2021](https://research.google/pubs/personalized-keyphrase-detection-using-speaker-and-environment-information/) | 關鍵詞、說話人、噪音／環境資訊，降低非使用者或背景的誤觸。 | 語者辨識與個人化減誤觸不是新方法。語者正確也可能是家人在閒聊，需測語意混淆。 |
| [ZP-KWS，2026-09-17 版本](https://arxiv.org/html/2606.20106v2) | 自訂關鍵詞、單句語者註冊、說話人 gate、相似詞與 FAR／FRR；作者含台灣單位。 | 作者所在地不代表實验資料是台灣家庭台語。研究已做自訂詞與個人語者；本题不卖這些功能，改測功能意圖與同一位家人的非指令。 |
| [When Speakers Are All Ears，PoPETs 2020](https://www.petsymposium.org/popets/2020/popets-2020-0072.php) | 播放電視節目，研究智慧音箱非喚醒詞的誤啟動。 | 電視誤觸與每小時誤觸評估均已有；不能只換台語節目當差異。 |

可保留的差異是「家人少量正負例的採集成本，與同一說話人的真正命令／否定／轉述拒絕表現」這組家庭實驗，沒有宣稱新模型或全球首次。另一位代理人獨立查上述原作後也認為這是可測的應用差異。

### 最小家庭試點與對照

- 固定同一種明確啟動方式，先用錄音片段與模擬開關展示。語音內容完全相同時，單靠音訊無法推知真正下令或引用；不承諾理解所有言外之意。
- 建議 2 位家人、2 個意圖、3 個不同日期，約 260 段短錄音：每人第一天每意圖 5 段加 20 段易混淆非指令；第二天每意圖 10 段加 20 負例；第三天每意圖 10 段加 40 負例。這是試點估計，不是統計保證。
- 三天使用不同語句，第三天加入不同距離与家庭噪音。人工標明指令／非指令；負例包含否定、轉述、近音詞與普通聊天。錄音按原始檔與日期分組。
- 比較 A 公開模型＋門檻、B 加少量家人正例、C 加家人正負例。門檻僅由驗證資料選，最後比較相同指令召回率下的誤接受率，以及校正段數、延遲、各家人的退步或改善。
- 短錄音的誤接受比例不能換算成常開裝置每小時誤觸；若選題後要常開版，需另做連續背景測試。公開語音不代表自己的房間、自己的家人口音。

## 已查但不列候選：家庭錄音品質／降噪選擇

[TMHINT-QI 原作者](https://github.com/yuwchen/InQSS)與 [VoiceMOS 2023 的第二版切分](https://github.com/dhimasryan/TMHINT-QI-VoiceMOS2023)的確提供台灣華語可用的語音品質及可理解度標籤。

此次下載官方 [VoiceMOS 切分壓縮檔](https://www.dropbox.com/scl/fi/ql5qedc832xc6potypr88/VOICEMOS2023_DISTRO.tar.gz?rlkey=yoj7gkdo1l97wmhdhhdc7lepz&dl=1)，169,114 bytes；`TRAINSET` 共 11,053 行，含表頭，實際 11,052 個評分記錄。欄位為 lisID、method、uttr、snr、noise、quality_score、intelligibility_score、file_name。`train_avg_mos.csv` 8,202 行含表頭，即 8,201 個聚合項目；不能將評分行數說成全是不同音檔。

亦用 HTTP Range 查 [原作者音訊 ZIP](https://drive.google.com/file/d/1TMDiz6dnS76hxyeAcCQxeSqqEOH4UDN0/view)：總大小 2,278,236,226 bytes，ZIP 19,850 條目，其中 14,915 個非 macOS 資源的 WAV；只讀中央目錄、原始評分 CSV 與一段 WAV，共約 2.99 MB，沒有下載整個 2.28 GB。原始 CSV 有 24,408 個主觀評分記錄；11 行 quality_score 空白。本次實讀 WAV 為 16 kHz、單聲道、32-bit IEEE float、2.786375 秒。一般只支援 PCM 的讀取工具會報 format 3，這是浮點格式，不是資料損壞。

沒有把可訓練資料存在當成選題差異：

- 原 [InQSS 2022](https://www.isca-archive.org/interspeech_2022/chen22i_interspeech.pdf)已聯合估品質與可理解度。
- [Whisper 語音評估，2023](https://arxiv.org/abs/2309.12766)及第二版已考慮未知噪音／增强系統。
- [VoiceAssist，Adobe／CHI 2019](https://research.adobe.com/publication/voiceassist-guiding-users-to-high-quality-voice-recordings/)已用品質指標引導家庭／非專業錄音設定。
- [NeuroAMP，2025](https://arxiv.org/abs/2502.10822)已做個人化聽覺增益與噪音環境。

因此普通降噪評分或「選比較清楚的設定」暫不列供挑選，保存已實讀資料供未來有更具體問題時使用。程式 MIT 不直接等於音訊資料也為 MIT；若重新納入仍需確認資料再利用條款。不要把評分標籤當成真實聽力障礙診斷。

## 已查但不列候選：家庭 LINE 謠言分類／查核助理

- [Cofacts 官方資料](https://huggingface.co/datasets/Cofacts/line-msg-fact-check-tw)是台灣通訊訊息、社群查核回應及關聯，CC BY-SA 4.0；來源卡可讀，但當前檔案需登入並同意資料使用者條款，未下載樣本。沒有代使用者提供聯絡資訊或同意條款。
- [官方使用教學](https://zh.cofacts.tw/tutorial?tab=check-rumors)與 [Cofacts.ai](https://cofacts.ai/)已有轉傳訊息查核、分類及 AI 撰寫回應。只換家族群組或 RAG 介面不足。
- [2026 作者實作 Narrative Latency TW](https://github.com/natharzu/narrative-latency-tw)已用同資料研究不同選舉週期的回應速度；普通訊息回覆等待時間分析也不保留。
- 訊息日期／數字更改、錯套舊查核的辨識另需人工建立成對真值、讀取完整既有檢索方法；本輪沒有查到足以支持完整特色的證據，不列已通過題。

## 已查但不列候選：AI 尋寵／領養配對

- [農業部遺失寵物資料](https://data.gov.tw/dataset/77682)有照片 URL 等公開欄位，但並不直接提供遺失照與收容照的同一隻身分配對標籤，本次不讀取飼主聯絡資訊。
- [Where Is My Puppy?，2015 原文](https://arxiv.org/abs/1510.02781)已研究遺失狗臉比對；[PetFace，2024 原作者](https://dahlian00.github.io/PetFacePage/)已有跨個體、未見身分驗證資料與基準，資料需學術申請，沒有取得。
- 台灣 [Petder 原廠](https://petder.petpark.com.tw/)已有生活方式與居住條件的 AI 領養配對。沒有已查證的不同家庭任務與可信標籤時，尋寵／領養推薦均不保留。

## 查核範圍

搜尋原作者 Hugging Face／GitHub、語音會議原文與研究機構、官方產品及資料頁。主要詞：TaigiSpeech personalized noise out-of-domain、Taiwanese personalized keyword spotting、台語 語音 指令 個人化 誤觸、TMHINT-QI personalized speech quality、VoiceAssist、Cofacts temporal retrieval、PetFace Taiwan lost pet recognition。

未完整查看本課所有歷屆作品、所有付費產品與未公開論文。候選保留只代表有資料與可測比較，不代表已證明改善或全球原創。

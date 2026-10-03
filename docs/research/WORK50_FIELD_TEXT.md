# 工作題補充：現場照片核對與學校教室餘裕

查核日期：2026-10-03（臺灣時間）。暫用 F01–F04，正式 W 編號由主代理整合；全部是未選定候選。保留 3 個現場照片方向及 1 個臺灣學校規劃方向，沒有為湊 5 題把授權／標籤不足者列入。

**證據狀態：以下均已讀來源、授權與實際資料樣本；尚未訓練、尚未驗證自家效果。** 小張圖片樣本放在已忽略的 `data/research-field-samples/`，不隨檔案提交；沒有下載完整大型影像資料集、開帳號、接受額外條款或外部上傳。數值 JSON 僅於記憶體讀取。F01、F04 的訓練源是臺灣；F02、F03 是海外源，限下述具體共同情境，必須另採臺灣現場照片才能證明適配。

## F01 手持拍攝車牌時，先判斷是否拍完整、哪邊需要留空間

- **工作用途／最低成果**：車隊交車、租車點交或維修接車的人員拍一張車牌特寫，得到「可留存／須退後重拍」及可能被切掉的方向，減少回到車旁補拍。普通輸入是一張手機照片，沒有改裝攝影機或取得車籍的要求。
- **公開資料／臺灣情境**：[TLPD 原作者資料](https://huggingface.co/datasets/evan6007/TLPD)，2025 年臺灣車牌影像，來源卡列超過 3,000 張、MIT 授權；此次 API 版本 `00f9ae2fa3d186bcf74e7f6ef4f48280181d6e85`，最後修改 2025-06-16。可直接讀 `images/` 與 `labels/`，不必執行其自訂載入程式。[圖片](https://huggingface.co/datasets/evan6007/TLPD/resolve/main/images/001HLA(0)(1).jpg) 與 [LabelMe 標註](https://huggingface.co/datasets/evan6007/TLPD/resolve/main/labels/001HLA(0)(1).json) 均 HTTP 200 且已讀：111×100 像素、`shapes.label=carplate`、四點多邊形。它沒有天然車牌號碼字串、攝影機 ID 或真實補拍結果標籤。樣本 `imagePath` 與檔名不同，配對時須另核對影像尺寸／內容，不能盲目相信字串。
- **實際可訓練目標**：由多邊形訓練車牌邊界模型；只取人工確認原圖車牌完整的子集，對原圖作已知方向裁切，建立「多邊形保留比例／左、右、上、下被切掉」的**代理標籤**，再訓練完整性分類。此標籤是可重現的裁切結果，不能寫成天然手持缺角標籤，也不能當 OCR 文字真值。原圖已切掉的內容不可推回。
- **已有人做什麼**：[同作者 FPGA-LPR](https://github.com/evan6007/FPGA-LPR) 已做關鍵點、透視矯正與 LPRNet 文字辨識；[中央大學手機車牌辨識論文](https://ir.lib.ncu.edu.tw/retrieve/77754/index.html) 已處理遠近、角度與相似字元。[Axis 拍攝指南](https://whitepapers.axis.com/en-us/license-plate-capture) 與 [Synology 車牌辨識管理指南](https://global.download.synology.com/download/Document/Software/AdminGuide/Package/SurveillanceStation/All/cht/DVA_License_Plate_Recognition_AG_cht.pdf) 已要求完整視野；因此「一般辨識／相機安裝建議」淘汰，不宣稱完整性概念首次出現。
- **這題另測什麼／對照**：固定車牌偵測模型，比較偵測信心、預測多邊形與畫框邊緣的幾何規則，以及裁切代理訓練後加本機校正的模型。測試的是**同一手機確實少補拍幾次、是否錯收缺角照片**，並非 OCR 準確率。報缺角錯收率、完整照片被拒率、方向判斷、每輛拍攝次數與中位完成秒數；如果幾何規則同樣好，模型差異不成立，應淘汰。
- **自家採集／成本／切分**：先採 10 輛試點，再以至少 30 輛授權車輛、2 支手機、每車 3 種距離／角度形成實拍集；由兩人確認完整與缺角，量每次補拍時間，約 1–2 小時拍攝加人工核對。依車輛／原圖羣分割，相同號碼與全部增強同組；另留手機或日期作測試。公共代理測試與天然實拍分開報，不用人工裁切假稱現場效果；原始車牌照片留本機，檔案只報彙總。

## F02 裝置盤點時，避免把警語、零件標籤當成裝置自身銘牌

- **工作用途／最低成果**：財產管理或維修人員在裝置上看到數張標籤時，先篩出可能的製造商銘牌；對零件標籤或不確定照片要求人工確認。普通輸入是 1–3 張近照。最低成果是「銘牌／其他／不確定」分類及錯收案例，沒有型號、序號或額定值自動填表承諾。
- **公開資料／版本／授權**：[Pompax classification](https://huggingface.co/datasets/kahua-ml/pompax-classification)，CC BY 4.0；[Mevaco 原始來源](https://universe.roboflow.com/mevaco/pompax_class) 也明列 CC BY 4.0。HF 版本 `a7b90449adc3a410999fce3c79c205ba4472469b`，2025-07-02；卡列 2,772 張，分割 2,502／34／236。真實欄位是 `image_id,image,label`，類別 0=Unlabeled、1=inne（其他）、2=tabliczka-znamionowa（銘牌）；排除無標註類。類別分佈 2,525 銘牌／240 其他／7 未標註，須處理不平衡。此次公共預覽列與圖片已讀：首列是 `label=1`，影像為 Spectro 的零件／光學元件標籤，沒有人工核定文字轉錄。HF 數量含增強，與原源 1,104 張原圖、不同版本數量不可直接相加。
- **臺灣適用證據／界線**：來源卡語言為英文／波蘭文，樣本有歐洲裝置，拍攝國未逐圖確認，不稱臺灣資料。[東元小型馬達原廠英文手冊](https://www.teco.com.tw/assets/pdf/%E5%B0%8F%E5%9E%8B%E9%A6%AC%E9%81%94%E4%BD%BF%E7%94%A8%E8%AA%AA%E6%98%8E%E6%9B%B8%28EN%29.pdf) 使用相同銘牌與 V、Hz、A 等裝置身分欄位；臺灣的[銘傳裝置盤點指引](https://sdgs.mcu.edu.tw/archives/10177) 也要求現場銘牌特寫。這是共同物件類別與真實工作用途的證據，只支援先篩照片，不能證明海外版面或文字已適配所有臺灣裝置。限定英文／通用符號的機械裝置，中文銘牌效果須另測。
- **實際可訓練目標**：影像 → 真實銘牌／其他類別，公共分類模型可訓練；拒答閾值以自家人工確認的分類正誤校正。資料不提供字串、文字框、對應哪臺裝置的核定型號，不可拿來宣稱欄位 OCR 已有訓練標籤。
- **已有人做什麼／差異**：Mevaco 原來源已有分類模型與其來源測試分數，因此普通銘牌分類直接淘汰；銘傳已有人工作盤點流程。本題固定分類器，另測加入**本工作場所常見的零件貼紙、危險警告與內部財產標籤**後，能否在相同人工確認比例下少錯收。對照公共模型固定閾值、公共校正，以及少量現場難負例校正；報其他標籤錯收率、銘牌漏收率、人工確認量與每臺盤點秒數，不把來源公佈分數當本次效果。
- **自家採集／成本／切分**：至少 50 臺授權裝置，每臺正確銘牌與容易拍錯的其他貼紙各 1–2 張；裝置管理者確認類別，約 2–3 小時。先 20 臺校正，剩餘裝置獨立測試，另留廠牌／場地；同臺、同張原圖及其增強不可跨組。只有公共資料只能展示分類，**本題差異必須依靠現場難負例**；若無現場存取或分類規則不一致，退回不採用。

## F03 外箱條碼上貼透明膠帶後，何時值得換角度補拍

- **工作用途／最低成果**：倉庫收貨人員掃 Code128 外箱編號，系統在反光遮住線條時判斷「目前可核對／再換一個角度」，兼顧錯收與拍攝成本。普通輸入是手機拍外箱條碼的短連拍；限工作場所實際使用 Code128 的編碼，不代替物流商追蹤系統。
- **公開資料／授權／真值**：[Dynamsoft UPS Synthetic Labels 子集](https://github.com/Dynamsoft/datasets-from-dynamsoft/tree/main/UPS-Synthetic-Labels) 的 [README](https://raw.githubusercontent.com/Dynamsoft/datasets-from-dynamsoft/main/UPS-Synthetic-Labels/README.md) 明列 CC BY 4.0、2025 年、18 個**合成 UPS 版面與編號**，不是天然貨運或個資。此次 [JSON](https://raw.githubusercontent.com/Dynamsoft/datasets-from-dynamsoft/main/UPS-Synthetic-Labels/annotation/annotations_min.json) 成功讀取，`images` 有 58 張、每張記錄條碼 `format,text,points`；[IMG_8747.JPG](https://raw.githubusercontent.com/Dynamsoft/datasets-from-dynamsoft/main/UPS-Synthetic-Labels/images/IMG_8747.JPG) 下載與像素已讀，有兩個 Code128 和一個 MaxiCode。圖片是上述合成標籤的照片角度／光照變體；**標註座標為零的佔位值，不能當有效框標籤訓練定位**。此子集授權不能外推到整個倉庫其他子集。
- **臺灣適用證據**：[GS1 Taiwan 載體標準](https://www.gs1tw.org/twct/web/retail-standard.jsp?menuactive=1) 列出國內使用的 GS1-128；其[官方實用手冊](https://www.gs1tw.org/twct/backend/downloadfiles/GS1_User_Booklet.pdf) 說明其以 Code128 符號為基礎。共享的是線條與解碼結構，UPS 欄位版面、MaxiCode 與合成地址不代表臺灣物流單。公共 Code128 字串可作光學核對前訓練；GS1 的 FNC1／應用識別碼語義須另外建立，不宣稱此資料已含。海外拍攝地未列。
- **實際可訓練目標**：固定既有解碼器，將輸出與 JSON 的編碼字串比對，建立「這次實際讀對／未讀到／讀成別個碼」標籤，再以影像與解碼品質特徵訓練可靠性模型。人工加的眩光、遮擋只列代理增強；真實透明膠帶資料須另拍。因公開僅 18 種標籤，不足以單獨宣稱通用可靠度。
- **已有人做什麼／差異**：[Dynamsoft 多幀交叉驗證](https://github.com/dynamsoft-docs/barcode-reader-docs-mobile/blob/main/programming/objectivec-swift/user-guide/capabilities/multi-frame-cross-filter.md) 已做多幀核對；[2020 年 shipping-label quality 論文](https://arxiv.org/abs/2008.11440) 已以影像區域性／整體品質辨識難讀標籤。因此通用 confidence、多幀投票與一般標籤品質題淘汰。此題只驗證**自家貼膠帶方法、印表機與手機的補拍策略**：在相同錯收率下，校正後能否減少反覆同角度拍攝的張數與時間。
- **最小對照／指標**：同一解碼器，固定最多 3 次：單拍、固定同角度多拍、通用多幀核對，以及含現場校正的換角度選擇。報確實錯收編碼的比例、未讀率、每箱照片數、完成秒數與條件別差異。若測試未發生錯讀，誠實報零次與樣本數，只能比較未讀與成本，不能宣稱已證明低錯收風險。
- **自家採集／成本／切分**：由印表機原始編碼檔／人工雙重核對提供真值，採 30–50 種無客戶資料的工作標籤，分無膠帶、透明膠帶、皺摺膠帶，2 支手機、數角度，約 2–3 小時。公共按 18 種標籤身分分組；自家按編號、同一實體箱及印表機／紙卷分組，保留未見箱與另一拍攝日測試。重複照片不可隨機跨組。若現場改用 QR／EAN 或沒有貼膠帶工作流程，此題不保留。

## F04 學校升年級時，人數變動會喫掉多少教室餘裕

- **工作用途／最低成果**：教務、總務或校務行政人員輸入學校程式碼、可用普通教室數及自己確認的規劃容量，檢視下一年二至六年級原有學生羣的人數區間，以及哪些年級可能需要保留額外一間教室。沒有要求個別學生名冊；最低成果為分年級誤差／區間與容量情境分析，不自動決定分班、裁併校或聘員。
- **臺灣公共資料／授權／樣本**：[教育部國民小學校別資料 6240](https://data.gov.tw/dataset/6240)，臺灣學校、政府資料開放授權第 1 版、103–114 學年逐年 CSV；107 年起另有 JSON，每學年一筆／校。詮釋資料更新 2026-02-02。本次真正讀到 [113 JSON](https://stats.moe.gov.tw/files/detail/113/113_basec.json) 2,668 校與 [114 JSON](https://stats.moe.gov.tw/files/detail/114/114_basec.json) 2,663 校，約 1.87／1.99 MB；113 有 BOM，移除後解析成功。真實欄位包括學年、學校程式碼、縣市、各年級男女學生數及班級數。例：011301 的 113 學年一年級 70 人，114 學年二年級 69 人，兩年皆 2 班。沒有房間大小、可用教室、轉出理由或最優分班標籤。
- **實際可訓練目標**：同校上一年級人數 → 隔年下一年級的**實際人數與變動量**；一年級新生另有來源問題，先排除。模型可學同屆升級殘差與預測區間，不把官方未來預測值當真實訓練標籤。教室需求是用操作者提供容量換算的情境結果，並非資料已有合法容量或空間需求真值。
- **已有人做什麼**：[教育部 114–129 學年預測報告](https://stats.moe.gov.tw/bookcase/St_report/114/index.html) 已以人口、入學與年級流失率預測全國／縣市學生數；[早期官方國教預測](https://teric.naer.edu.tw/wSite/PDFReader?fileName=1508303836807&format=pdf&xmlId=1988877) 也已有分年級模型。一般少子化總量預測與做一張學生數儀錶板淘汰。
- **這題另測什麼／對照**：檢驗**校別轉入轉出造成的餘裕損失，以及少數校史時該借用多少同縣市資訊**。對照全數直升、縣市共同升級率、單校歷史率，以及收縮／分位模型；報逐校逐年級 MAE、小校區間涵蓋率、區間寬度，以及在使用者容量下「少預留／多預留一間」的次數。容量成本分開做敏感度分析，不能用同一學生源換門檻再算多題。
- **成本／獨立驗證／限制**：公共模型不需私有資料。真實教室用途需另盤點一校普通教室數、特殊用途佔用與可調整房間，約半天校內走查；只量房間與彙總人數，不收學生個資。訓練先用較早學年，留 112–114 年作向前測試，另留完整學校程式碼羣驗證陌生校。正式訓練須逐一讀 103–112 原檔，本次只抽核兩個近期完整年度，未宣稱已建全歷史。學校程式碼變更、整併或停招須查證或排除，不把缺列當零人；只有最多 12 年的單校紀錄，不能保證長期規劃。

## 未計入的來源與查重範圍

- **有號碼字串的臺灣車牌資料**：[EZCon](https://huggingface.co/datasets/EZCon/taiwan-license-plate-recognition) 公共預覽真有 `license_number`、`xywhr` 與 1,812／518／259 分割，樣本已讀；但來源卡未列可核定資料授權，不能把別個 TLPD 的 MIT 移過來。因此未列「跨攝影機保持 OCR 號碼」題。
- **工業文字欄位資料**：[industrial-text-detection](https://huggingface.co/datasets/kahua-ml/experimento3-industrial-text-detection) 的實圖／bbox／FABRICANTE、SN、MODEL 等區域類別已讀，沒有字串真值；卡要求查原授權，[Roboflow 原源](https://universe.roboflow.com/marcos-feria/experimento-3) 本次回應 403，授權未確認。不能轉成 F02 型號欄位訓練。
- **貨櫃碼**：[BIC 識別碼結構](https://www.bic-code.org/identification-number/) 與 [長榮臺灣 EMCU 登記](https://www.bic-code.org/bic-codes/emcu/) 已確認共用標準；但 [ContainerNumber-OCR](https://github.com/lbf4616/ContainerNumber-OCR) 未列資料授權，[SAFEContain](https://github.com/m-fol/SAFEContain) 的程式 MIT 不等於照片授權。此次未讀到同時具可用授權與原字元標籤的下載樣本，故不列正式 OCR 題。
- **水／電表**：臺灣公開數位／智慧電表安裝統計不是讀值影像。[SCUT-WMN](https://github.com/HCIILAB/Water-Meter-Number-DataSet) 是中國水錶資料，限制非商業研究，既有方法已處理轉輪中間狀態；本次沒有證明同型臺灣表面適配或讀下載標籤，未列。
- **其他條碼**：[mapo80/barcodes](https://huggingface.co/datasets/mapo80/barcodes) 雖卡列 CC BY-SA 4.0，預覽為實圖與合成碼混合，未讀大 ZIP 的有效位置／字串真值；[BarBeR](https://github.com/Henvezz95/BarBeR) 已有多種真實條碼基準，但原下載需登入，本次未取得。沒有把展示圖當已取得全套訓練資料。
- **消防備案**：[內政部資料 12096](https://data.gov.tw/dataset/12096) 頁面有 95 年起歷史查詢說明、政府開放第 1 版；本次直接 CSV 成功讀到的卻是 **107 年 1–5 月及分月切片**，不是完整 95 年至今。未完成歷史下載與獨立學習目標，沒有為補數量列為月量預測。
- **可取得學校作品／課程範例**：實查臺灣學校公開專題、論文及科展，搜尋包含 `site:edu.tw 車牌 拍攝 完整 專題`、`site:edu.tw 銘牌 辨識 專題`、`site:edu.tw 條碼 影像 專題 反光`、`site:edu.tw 國小 學生數預測 年級`。[臺大 2024 移動車牌論文](https://tdr.lib.ntu.edu.tw/handle/123456789/92928?mode=full) 已做角度／移動模糊，[新化高工自動化停車專題](https://www.hyivs.tn.edu.tw/ischool/public/resource_view/openfid.php?id=3040) 主要是 PLC／模擬停車；[清華工工專題摘要](https://ieem.site.nthu.edu.tw/var/file/310/1310/img/1892/526811540.pdf) 的相關作品用產品外觀替代條碼，[科教館條碼作品](https://www.ntsec.edu.tw/science/detail.aspx?a=90&cat=19270&sid=19390) 是彩色 QR 多張掃描。這些不是授課老師指定範例，不據以增訂評分條件；沒有查到相同現場校正實驗也不代表原創。

四題都有可訓練模型與工作分析目標；代理人可協助整理「應補拍／應人工確認／容量情境」，其猜測不能充當訓練標籤。課程代理人最低要求仍依專案原有老師證據，不在本分支自行判定。

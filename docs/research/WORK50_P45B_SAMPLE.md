# P45B溫度資料：最小取得查核

查核日期：2026-10-03。只核對工業I12資料取得；未修改工業檔或主清單，未登入、取消憑證驗證或下載整包／大型MAT檔。

**結論：公開檔案清單與4.84KB官方說明檔已讀，但P45B原始量測值／MAT檔頭仍未取得。** 目前不能把I12記為原始樣本已讀；若正式清單要求此次真數值樣本，應暫緩或替代。

## 確認到的公開入口

[Mendeley V2](https://data.mendeley.com/datasets/k86rymk5kn/2)頁面列2026-09-17、DOI `10.17632/k86rymk5kn.2`、CC BY4.0、英國Warwick來源。正常公開瀏覽器能展開 `Data/P45b`，沒有要求登入；整包Download All為4.04GB，沒有點擊。

| 公開P45b檔名 | 頁面大小 | 此次狀態 |
|---|---:|---|
| `2C_P45b_data.mat` | 301MB | 檔名／單檔入口已見，未下載 |
| `3C_P45b_data.mat` | 282MB | 檔名／單檔入口已見，未下載 |
| `4C_P45b_data.mat` | 278MB | 最小已處理檔，嘗試Range但HTTP403；未讀MAT標頭 |
| `raw_P45b_data.mat` | 495MB | 原始量測檔入口已見，最後一次Range仍HTTP403；未讀MAT標頭 |

[4C檔案資訊頁](https://data.mendeley.com/datasets/k86rymk5kn/2/files/9456e718-0acf-4512-a44f-48d0ef71f4af)列上傳2026-09-14、CC BY4.0，宣告SHA-256為 `aacad59a8f7dc7f952e34798600342cb1f091bc2c2db0c82c622e7010ce77f5c`；這只是來源宣告，沒有對完整檔自行驗證雜湊。

最小檔的[正式單檔下載入口](https://data.mendeley.com/public-files/datasets/k86rymk5kn/files/9456e718-0acf-4512-a44f-48d0ef71f4af/file_downloaded)以一般HTTP串流加 `Range: bytes=0-65535` 嘗試，HTTP403，僅讀約3.3KB拒絕回應後關閉。這不是MAT檔內容，不能算量測樣本。檔案預覽只停留Loading，未讀出矩陣。

最後另對[raw原始單檔入口](https://data.mendeley.com/public-files/datasets/k86rymk5kn/files/2ecb3567-e8ee-4c03-99f5-03b02715444d/file_downloaded)作同樣64KiB上限Range嘗試，仍HTTP403、`text/html`、實讀3,312bytes拒絕回應後關閉，沒有MATLAB標頭。停止延伸下載。

## 小型官方說明已實讀

`Code`另列 `main_data_process.m` 5.15KB、`main_plot_example.m` 2.08KB、`param_batt_fos.m` 7.06KB與 `read_me.md` 4.84KB。本次只讀[read_me.md資訊頁](https://data.mendeley.com/datasets/k86rymk5kn/2/files/68f0b420-16aa-44bc-83eb-807c94973043)對應的官方公開下載重導檔；沒有執行其程式。

瀏覽器的小檔下載導向公開S3位置，但下載工具逾時、瀏覽器顯示ERR_BLOCKED_BY_CLIENT；沒有修改瀏覽器保護設定。該正式公開重導URL用一般HTTP Range取得HTTP206，`Content-Range: bytes 0-4951/4952`，實讀4,952bytes Markdown，僅在記憶體解析，未保存來源檔。說明內容可確認：

- P45b不同電流條件在**同一次連續試驗**中依序進行；完整電池測試儀與光纖原始紀錄只存一份 `raw_P45B_data`。不能把2C／3C／4C先當獨立電芯。
- 各電流條件分割檔含 `data_sync`、`data_splitted`，不是完整raw資料副本。這是說明檔提供的結構名稱，尚未用MAT欄位自行驗證。
- 處理流程先同步電池測試儀與分佈式光纖資料，再選取纏繞區段、套用該型電芯匝數及幾何，最後插值成軸向×圓周網格。
- 插值網格點數不等於原始光纖測點數。各網格值不能當獨立感測器直接測得的金標。

## I12仍缺的實際樣本與表述修正

尚未讀到原始時間向量、測點位置／間距、溫度矩陣數值及單位、循環界線／個數、電流欄位、取樣頻率或MAT版本，不能填入猜測格式。

若繼續I12，目標應區分「重建網格最高值與位置」和「原始光纖實測點最高值與位置」；兩者都不是未量測的整個連續表面最高溫真值。兩點虛擬感測器比較須先核對原始位置及同步時間；若拿插值網格作訓練參考，應稱重建代理標籤，不能因網格更密便宣稱真值更完整。

目前可確認同一連續試驗的不同電流分段，但完整充放電循環及實體電芯數還沒有樣本證明；切分只能在真正循環／電芯識別確認後設計，不能用檔名直接證明跨電芯測試。此次補證仍不足把原始資料取得缺口關閉。

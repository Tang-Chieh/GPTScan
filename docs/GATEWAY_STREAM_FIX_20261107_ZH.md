# Gateway 串流處理修正（2026-11-07）

## 範圍

僅修改 `src/model_transport.py` 的傳輸／協定處理，並新增 `tests/test_gateway_stream.py`。不修改 GPTScan 的 rules、原版判定流程、基礎或 price system prompt、FirstDeposit checker、編譯／archive adapter、PredictionCase 內容映射或 Judge。

這是 baseline 的模型連接適配修正，不是增加漏洞偵測能力或重問語意問題。

## 已知歷史問題與證據限制

在 `dataset-23-minimal-baseline-20261106` 的 Behodler 紀錄中有7筆 `invalid_response`，但當時只保留泛稱 `Model stream failed or was incomplete`，無法回溯區分 `error`、`response.failed` 或 `response.incomplete`，也沒有保留明確原因。因此不能宣稱此次已證明並修復那7筆的唯一根因。

同次執行另有單次timeout與夜間長時間空檔；這些不是單靠SSE parser就能解決。本次沒有改動既有執行時限或重跑舊實驗。

## 修正內容

1. **SSE framing**：依空白行分隔事件，合併多個data欄位；支援CRLF、初始UTF-8 BOM、comments／heartbeat與event header。只有完整terminal response才能成功，delta或DONE不能充當完整回答。
2. **分開原因**：區分EOF缺少completed、連線中斷、外層event JSON錯誤、server error、內容／長度限制、登入／權限問題。記錄只含安全分類，不記錄provider自由文字、partial answer或憑證。
3. **有限傳輸重試**：EOF／連線中斷、明確暫時server failure、外層event協定破損，額外重試最多一次。使用相同model、system instruction、question與request body，不改內容、不挑最好回答。
4. **不盲目重試**：max_output_tokens、content_filter、context-length、登入／權限／明確不可恢復失敗、無原因的incomplete不自動重問，不提高輸出限制，不切模型或API。
5. **保留失敗**：重試仍失敗時回到原版候選級例外處理，錯誤仍會記錄。合法HTTP成功下模型自行回錯JSON，不是串流故障；client原樣交回原版GPTScan解析，不另作語意修復。

既有HTTP429／5xx／網路重試策略未在此次重新設計；完整GPTScan單次問答仍受原有外層wall timeout控制。重試不重設外層時間預算。

## 驗證

新增15項protocol tests，加上既有47項，共62項unit tests通過。測試覆蓋SSE多行、BOM／CRLF、缺少completed、連線reset、server error相同請求重試、連續失敗停止、登入／內容／長度限制不重試，以及不修復模型回答。

完整synthetic compiler＋本機假模型5種流程通過，輸出由正式benchmark_eval contract驗證。真實gateway smoke的結果保存在 `outputs/gateway-stream-fix-20261107/live_smoke.log`；該測試只檢查兩個短請求，不等於已重新分析Behodler或已證明長時間執行完全無中斷。

沒有修改共享OMP gateway服務、重新登入、commit或push。既有實驗結果與Judge報告均未覆寫；若之後使用此連接版本重跑，須另開結果目錄並披露修正版，不能替換舊結果冒充原始run。

## 官方協定參考

- [OpenAI Responses streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events)
- [OpenAI streaming guide](https://developers.openai.com/api/docs/guides/streaming-responses)

上述文件用來核對事件語意；本機OMP是相容gateway，文件並不保證其服務行為或本次歷史錯誤根因。

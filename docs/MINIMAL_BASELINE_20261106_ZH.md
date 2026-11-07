# GPTScan 最小適配 baseline（2026-11-06）

只為三個目的改動：dataset repo 接入、price focus、直接輸出 Judge input。不優化漏洞偵測或原版 checker。對照 upstream `29a174773bd526c32ab7d6a8c78a63870330ccc7`；這是 adapted baseline，不是原論文完全重現。

## 撤回的額外行為

- 移除一次 failed event 後全域拒絕後續模型請求的機制。
- 不因任意 ERROR log 而禁止合法 PredictionCase 輸出。
- 恢復原版 yes/no、numbered choices、static-variable JSON 解析，不強制額外型別或重答。
- 撤回 rule index 修正，恢復原版 function_data 索引，不混入偵測 bug fix。
- 恢復原版基礎 system prompt，只附加既有 PRICE_SCOPE。
- 移除 CandidateRejected 分類，恢復原版 catch／logger.error／繼續策略。
- 網路／429／5xx 採原版式持續重試，由明列的180秒單次問答及60分鐘repo預算限制；不換模型、不作語意重答。

FirstDeposit checker 保留原版字串與括號解析，未修 source slicing 或改成 IR checker。原始缺陷影響結果時另記錄，而非為提升成績修改。

已移除不再使用的 answer_validation、json_questions、rule_validation 模組。修改前 source／scripts／tests／docs 與 working-tree patch 存於 `outputs/minimal-baseline-checkpoint-20261106/`，沒有 Git commit／push。

## 保留且需披露的接入差異

1. 固定 repo ref、既有 Docker archives、strict／legacy 驗證、路徑快照與 scope。這是原本實驗的明確輸入範圍，不聲稱每個repo全部檔案覆蓋。
2. 保留讓23個archives可載入的 Falcon compatibility 層；沒有新增漏洞checker，部分新EVM表示仍有限制。
3. 保留檔案／contract／signature 身分與 Falcon resolved CallGraph，以處理dataset的overload。這不是原版Java name-only graph，可能影響caller context，不能宣稱核心完全未改。
4. 七條upstream規則只補output.impact；recommendation不改，直接映射mitigation。
5. 經授權的本機gateway取得指定gpt-5.6-luna回覆，協定轉回string；沒有API key／模型fallback。
6. 直接輸出PredictionCase，做身分、程式位置、欄位映射與輸出格式驗證；不人工或LLM補寫finding。
7. 每repo60分鐘、單次問答180秒，是明列的實驗設定，不是原版預設。

## 完成與錯誤分開記錄

| 狀態 | 意義 | Judge |
|---|---|---|
| completed | 程序結束且有合法輸出，未記錄分析錯誤 | schema通過後可評估 |
| completed_with_errors | 依原版容錯跑到結束，有合法輸出，但部分分析出錯 | 評估實際輸出並披露不完整性 |
| failed／timed_out／schema_failed | 程序未正常結束、超時或輸出無效 | 不捏造空input、不用舊結果替代 |

processing_completed與analysis_complete分開保存。ERROR數量不是失敗候選數，一個問題可能產生多條log。

保留既有evaluator、gold ground truth與分數設定，不因partial狀態改寫prediction verdict或Judge prompt。任一repo沒有有效輸出時，完整23-repo Judge先暫停，不默默縮小dataset。

不根據ground truth調整規則、不挑最好一次、不自動重跑到成功。新實驗23個repo用同一版與預算，舊結果不混入。

## 驗證與實驗

- 七條規則扣掉impact後與upstream YAML結構一致。
- 三個static-question functions的AST hash與upstream相同；確認原版基礎prompt、無全域封鎖／ERROR veto、未優化FirstDeposit。
- Synthetic compiler＋本機假模型測試：正例、陰性、格式錯誤、原版predicate rejection、格式錯誤不再重問。
- 原版錯誤分支測試預期completed_with_errors，不再被額外保護判成整體失敗；保留診斷並驗證實際PredictionCase。

入口：`scripts/run_upstream7_experiment.py --run-judge --output-dir <新目錄>`。先OAuth smoke，再完整GPTScan，最後評估23份合法輸出。查看新目錄的README、workflow_status、gptscan/README與最終llm_judge/report.md。

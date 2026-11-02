# 驗證紀錄（2026-11-02，Asia/Taipei）

## 測試範圍

- Upstream GPTScan：`29a174773bd526c32ab7d6a8c78a63870330ccc7`。
- Falcon：`93c1be7914f24e5567ff17da45be6f87b506c069`。
- 本機：macOS ARM64，Python 3.10.17、Temurin JRE 17.0.21、Solidity 0.8.19。
- OMP gateway 18.6.0，指定 `openai-codex/gpt-5.6-luna`。
- 測試時沿用已授權的 Hound/SmartAuditFlow gateway runtime；沒有把 OAuth credentials
  複製進這個 fork，也沒有執行新的登入。

## 結果

| 項目 | 結果 | 證明什麼 |
|---|---|---|
| Adapter / transport / exporter unit tests | 15 tests passed | scope、path、防覆蓋、schema 欄位、錯誤處理 |
| Codex gateway live smoke | yes/no + JSON 通過，2 個真實請求 | 模型連線與 parser 格式可用 |
| Synthetic full pipeline | 成功，3 個真實模型請求，1 筆 finding | 編譯→Java→GPT→靜態檢查→PredictionCase 串接 |
| Synthetic compile metadata | compile_succeeded=true，analysis_errors=0 | 沒有以跳過 compiler 假裝成功 |
| Actual benchmark schema | PredictionCase.model_validate 通過 | 可被現有 evaluator 的 input model 讀取 |
| Real Wagmi repo prepare-only | 19 Solidity files，project root=concentrator | 現有 dataset 的路徑與 nested project 接口可用 |
| Real compiler/Java + fake-model regression | positive、negative、malformed 三種皆通過 | 正向可匯出、負向可正常空集合、格式錯誤不能冒充無漏洞 |

Synthetic full pipeline 成功那次耗時約 8.93 秒。fixture 是
`tests/fixtures/price-repo/Oracle.sol`，不是實際 dataset，也不是 Ground Truth。
它只有估值計算而無真實 lending 狀態變動，不能把該 finding 宣稱成已證明可獲利的 exploit。
實際 PredictionCase 範例保留在 [examples/synthetic_prediction_case.json](../examples/synthetic_prediction_case.json)。

Schema 驗證使用現有 `fffuuuming/prototype` evaluator snapshot `e46fc270` 的
`src/benchmark_eval/contract.py`；是直接載入該檔的 PredictionCase，不是只對自製示意 schema。
該版支援未加 verdict 的 legacy predictions；本次沒有把 heuristic finding 假標為 verified。

## 沒有做的事

- 沒有跑完 23 個 repo 的完整 benchmark；沒有產生任何新的 recall/precision 數字。
- 沒有呼叫完整 LLM Judge，也沒有產生新的 Judge report.md。
- 新機器的 OAuth login 與 pinned gateway installer 仍需依文件自行完成。
- CI unit tests 不需要模型；runtime regression 使用真實 Java/compiler 搭配 fake model，
  用來測 positive/negative/malformed 流程，不代表 LLM 推論品質。
- Java/solc assets、`.venv`、本機 gateway token、執行 log 與 dataset source 全部不提交。

若未來要做實驗比較，應另記錄 dataset/evaluator revision、每 repo completion status、
rules/profile/model 與所有失敗原因，不能只評估成功輸出的 repo 卻宣稱全 dataset 完成。

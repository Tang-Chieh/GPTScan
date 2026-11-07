# GPTScan 直接輸出 Judge input（2026-11-06）

## 現在的主要輸出

GPTScan 的 `-o` 現在直接寫出 canonical `PredictionCase`，不先落地原生 JSON 再用外部 script 轉換：

```text
GPTScan 規則／模型／static analysis
    ↓
記憶體中的 findings 與程式定位
    ↓
內建 exporter 組成並檢查 PredictionCase
    ↓
-o 指定的 JSON 檔案 → LLM Judge
```

`prediction_export.py` 仍是內部欄位映射與輸出模組，不是使用者需要另跑的轉檔步驟。沒有要求模型生成整份 PredictionCase，也沒有改動漏洞判定方法。

## CLI 使用

從 GPTScan 的 `src/` 目錄執行，路徑替換為實際位置；source-only 模式仍需正確 compiler／framework 環境：

```bash
../.venv/bin/python main.py \
  -s /path/to/repo \
  --repo-id example-repo \
  --repo-root /path/to/repo \
  --gateway-token-file /path/to/authorized/auth-gateway.token \
  --profile price \
  --model openai-codex/gpt-5.6-luna \
  --strict \
  -o /path/to/new-predictions/example-repo.json
```

`--repo-id` 現在是必要參數。輸出父資料夾需先存在；建議使用新目錄，避免把舊檔誤認為本次結果。送 Judge 的 predictions directory 只放逐 repo PredictionCase，不放 metadata 或 native debug JSON。

`scripts/run_reusable.py` 與 `scripts/run_dataset.py` 都已更新：直接以 `-o prediction_case.json` 呼叫 GPTScan，不需要外部轉檔，也不再預設產生原生 `output.json`。前者仍支援已驗證的 archive，不必重新編譯。

## 選用參數與錯誤處理

- `--native-output /path/to/debug/native.json`：選擇保存原生 `results` 結構，不是 Judge input。
- `--prediction-output /path/to/compat.json`：舊 CLI 相容選項，現在只是主要 PredictionCase 的同內容副本；runner 不再需要它。
- `<主要輸出>.metadata.json`：執行資訊，含 `output_format: PredictionCase`；不是 Judge input。
- Native debug、主要輸出與 metadata 路徑不可互相覆蓋。
- 編譯或分析不完整時不發布新的成功 Judge input；合法零結果仍可產生 `predictions: []`。
- JSON 使用 temporary file + atomic replace，避免讀到寫入一半的結果。

## 內容來源與版本

```json
{
  "repo_id": "example-repo",
  "detector_metadata": {
    "detector_version": "gptscan-price-upstream7-direct-v2",
    "llm_model": "openai-codex/gpt-5.6-luna"
  },
  "predictions": []
}
```

有 finding 時，predictions 會含 finding_id、title、description、impact、mitigation、vulnerable_code 等。程式位置來自解析／編譯定位；impact 仍是七條規則的新增模板，mitigation 直接取原版 recommendation。不做人工補寫或額外 LLM enrichment，也不讀 ground truth 產生 findings。

新版 detector version 區分七條規則與直接輸出設定，避免與原先 `gptscan-price-v1` 混用。

## 驗證

```bash
.venv/bin/python scripts/validate_prediction.py \
  --contract-file /path/to/prototype/src/benchmark_eval/contract.py \
  --prediction /path/to/new-predictions/example-repo.json
```

回歸測試覆蓋主要輸出、alias、native debug、合法零結果、模型格式失敗，以及用正式 benchmark_eval contract 驗證實際完整流程的 synthetic 輸出。測試使用本機假模型，不呼叫實際 LLM。

舊的 23-repo 204 findings 與 Judge report 均保留，沒有因本次修改重跑或覆寫。它們仍是舊規則／舊輸出的實驗結果。

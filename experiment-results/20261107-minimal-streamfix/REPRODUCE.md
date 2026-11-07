# 如何檢查與重現本輪實驗

這份目錄保存的是實際11/07結果，不需要先呼叫模型就能閱讀與查核。Predictor與Judge都具有模型隨機性；重跑不保證逐字或逐分數一致。

## 1. 先閱讀已完成結果

- `evaluation/report.md`：正式評估報告。
- `predictions/`：23份原樣PredictionCase；沒有額外人工補寫mitigation。
- `repo_summary.json`：9個completed、14個completed_with_errors，不表示全部候選成功。
- `evaluation/manifest.json`與`judge_artifact.json`：canonical原始評估證據，未重寫hash或分數。

原始sources／build cache很大且已由archive bundle保存，因此這份結果目錄不重複收錄。Source snapshot不含Python environment、OAuth憑證或模型token；`detector_source_snapshot/`是實驗當時的程式碼，branch後續的打包文件等可能不同。

## 2. 準備外部資料與環境

1. 在GPTScan根目錄依 `requirements-fork.txt` 建立Python 3.10 `.venv`；Java 17可用。
2. 準備已有的Reusable Dataset checkout，驗證時版本為`c95c1f7`，candidate repo版本需符合bundle manifest。
3. 準備我們專案prototype的獨立checkout，固定到evaluator commit `e46fc2702a1c6506f9a56af00990f8218648f697`；不可只拿任意最新版替換而不披露。該repo如為private，需要自己的讀取權限。
4. OAuth、gateway須自行授權，不包含在GitHub。依prototype的 `src/benchmark_eval/README.md` 完成Judge login；GPTScan gateway依本repo `docs/REPRODUCE_ZH.md` 準備。
5. 本地完整wrapper `scripts/run_upstream7_experiment.py` 保留原實驗的工作區預設路徑；別台電腦建議用以下公開CLI分段執行，不必模仿作者的絕對路徑。

固定版本、scope、必要Falcon相容層、七條原版rules＋impact與price prompt皆是本輪條件，不是原版論文設定。

## 3. 解壓已發布的23份archive

在GPTScan根目錄執行（輸出須為新目錄）：

```bash
.venv/bin/python scripts/unpack_dataset_inputs.py \
  --bundle dataset_inputs/23repos-20261105 \
  --output-dir outputs/reproduce-inputs
```

詳細source refs、strict／legacy及checksum說明見 `dataset_inputs/23repos-20261105/README.md`。重用archive的流程不需啟動Docker；要重新編譯才需要原image／build recipes。

## 4. 完整跑GPTScan

以下將路徑替換成你的實際位置，不包含任何登入secret：

```bash
.venv/bin/python scripts/run_reusable_batch.py \
  --plan outputs/reproduce-inputs/archive_plan.json \
  --reusable-root /absolute/path/to/prototype-reusable-dataset \
  --contract-file /absolute/path/to/prototype-at-e46fc270/src/benchmark_eval/contract.py \
  --token-file /absolute/path/to/authorized/auth-gateway.token \
  --model openai-codex/gpt-5.6-luna \
  --timeout-minutes 60 \
  --request-timeout-seconds 180 \
  --output-dir outputs/reproduce-gptscan
```

`predictions/`直接是Judge input；無須另跑output converter。請檢查全部23份皆有輸出且schema驗證通過，並另列completed_with_errors。不要將fatal failure或timeout捏造成空predictions。

## 5. 執行正式LLM Judge

在固定版本的prototype checkout執行，使用它本身的已安裝環境：

```bash
.venv/bin/python -m src.benchmark_eval \
  --ground-truth-dir dataset/downstream-stage1/pilot-v1/ground_truth \
  --predictions-dir /absolute/path/to/GPTScan/outputs/reproduce-gptscan/predictions \
  --output-dir /absolute/path/to/GPTScan/outputs/reproduce-evaluation \
  --auth-mode oauth \
  --judge-model gpt-5.6-luna \
  --weight-profile end-to-end-v2 \
  --temperature 0 \
  --batch-size 10 \
  --max-concurrency 4
```

這會真的呼叫Judge模型。若只想重新評估本次已發布的findings，把predictions-dir換成GitHub下載後的 `experiment-results/20261107-minimal-streamfix/predictions`，不必重跑GPTScan。

若只想從已有Judge artifacts重製Markdown報告，不需要模型：先將本目錄的`evaluation/`複製到新的本機output目錄，再從固定prototype執行 `python -m src.benchmark_eval --report-only --output-dir <該output>`。

本次打包未包含evaluator源碼或ground-truth獨立副本；canonical evaluation manifest已含本次實際配對的資料。需要重跑Judge仍應取得上面指定的正式prototype版本；可用evaluator_source_hashes.json查核快照檔案。

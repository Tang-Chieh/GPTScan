# Dataset → GPTScan 接入修正（2026-11-05）

本次處理 11/4 批次中 15 個失敗 repo。驗證目標是 archive、完整 Falcon IR、
source parser、函式定位與 CallGraph；**不是完整 GPTScan 模型分析或 LLM Judge**。
保留舊結果，不修改 candidate repo 或外部 Reusable Dataset checkout。

## 實測結論

最終 `verified-23` 回歸：**23/23 ready_for_analysis**，包含原先失敗的 15 個。
16 個使用 strict archive sidecar，7 個使用明確 source-compared archive 模式。
36 個單元測試、archive runtime 與五種 fake-model runtime regression 通過。
這些數字是接入與程式測試結果，不是漏洞檢測召回率；本次沒有真實模型請求、
新的 PredictionCase 或 LLM Judge。下一輪完整實驗應全部使用同一修正版本重新分析，
不要把 11/4 舊版本的 8 個結果和新版本結果直接當成同一組 benchmark。

## 修正內容

| 類別 | Repo | 做法 |
|---|---|---|
| 舊 archive | MarginSwap、Blueberry | 新增明確的 `--legacy-archive` 模式；核對 HEAD、embedded source 與既有 materialize recipe，記錄缺少舊 provenance 的限制 |
| Function overload | Vader、Behodler、Tokemak、Woofi | 用 compiler declaration 的檔案、contract、signature、source location 對應 function；使用 Falcon resolved calls，不再依 Java 的同名 function 合併結果 |
| Falcon AST／IR | 2022-09-notional、ParaSpace、Revert Lend、2024-04-panoptic | 修正 event/custom-error 名稱查找、tuple component types/空位、Yul declarations/literals、global using 與 compiler-ID library resolution |
| Compiler context | USSD、Dopex、Abracadabra、2025-12-panoptic | 保留 framework 原本編譯需要的完整上下文，不在編譯前刪除依賴；報告目標另外選擇 |
| Apple Silicon／amd64 | USSD | Node wrapper 透過 argv 傳入 `--no-opt --no-sparkplug --liftoff-only --no-wasm-tier-up`，不把 V8 flags 塞入不允許的 NODE_OPTIONS；保留 solc-js 所需 WASM |
| Brownie | 2021-08-notional | 隔離安裝 Brownie 1.21.0、setuptools 75.8.0；依 bounded pragma 選 image-bundled solc；擷取完整 compiler output，包含只有 struct/enum 的來源 AST，再匯出 archive |
| 新 Solidity／EVM | 2025-12-panoptic | 保留 global library bindings、依 compiler reference 降低 user-defined operators、補 Yul sibling function lookup、nested index ternary 與 Cancun builtins 的呼叫表示 |
| macOS 路徑 | Dopex | 大小寫不同的 Linux source paths 在 snapshot 使用獨立實體位置；保留 logical path mapping，PredictionCase 還原原始 repo 路徑 |

Falcon 修正在 `src/falcon_compat.py`，只支援測試過的 Falcon 0.2.28 /
Crytic Compile 0.3.3。不修改 site-packages 源碼、原始 archive、原始 source bytes，
不以忽略 IR errors 或假的 bytecode 換取成功。User-defined operator 只在 in-memory
AST view 轉成 solc 已明確選定的 function call，保留 source offsets。

## 舊 archive 的明確接入

```bash
.venv/bin/python scripts/run_reusable.py \
  --reusable-root /path/to/prototype-reusable-dataset \
  --repo-id 2021-04-marginswap \
  --legacy-archive /path/to/2021-04-marginswap_export_archive.json \
  --output-dir outputs/marginswap-preflight
```

這不是停用驗證：會核對 repo HEAD、實際存在的來源 bytes、recipe 宣告的
materialized files，拒絕 mismatch。Archive-only dependencies／generated sources 逐項列出。
但原始 compiler invocation／recipe **未取得新版 sidecar attestation**，manifest 的
`build_provenance_verified` 為 false，不會把 source comparison 冒充完整 provenance。
原本 `--archive` 的 strict sidecar 驗證仍保留。

需要限制 production roots 時可加 `--target-root src` 或 `--target-root contracts`。
會沿用 solc AST 的 `ImportDirective.sourceUnit` 計算必要依賴閉包；不是只留下
檔案本身、丟掉 imports。排除的是不可由 production roots 達到的 build scripts／tests，
選擇記在 `compiler_scope_selection.json`。這是明確的分析範圍，不代表整個 repo 每個檔案都分析。

完成接入後，相同 CLI 加上 `--run-analysis --token-file ... --model openai-codex/gpt-5.6-luna`
即可執行 GPTScan；本次修正測試沒有加這些選項。

## Compiler-context build

`scripts/build_compiler_context.py` 僅在 container 執行，沿用可信 build.json 的 setup、
compile、materialize 與既有 runner toolchain/cache helpers，在 ephemeral copy 操作。
它不宣稱通過原本 production-v1 pre-build pruning：
`compiler_context_policy=baseline-framework-inputs-v1`、`production_scope_validated=false`。
編譯輸出之後，再選明確 production roots 與必要 imports。

`scripts/rebuild_context_batch.py` 是本工作區重建入口，輸出獨立資料夾，不覆蓋舊結果。
Brownie 的 compiler capture / export 分別在 `brownie_capture.py`、
`export_brownie_capture.py`。完整 export 不再呼叫 compiler，並會拒絕缺少 bytecode 的
non-interface capture。Brownie 額外 ABI-only interface pass 不當成可執行 compilation unit；
正式 compiler units 仍保留被 import 的 interface AST。

## 可重現的 archive plan

```json
[
  {
    "repo_id": "example-repo",
    "archive": "/absolute/path/example_export_archive.json",
    "legacy": true,
    "target_roots": ["contracts"]
  }
]
```

```bash
.venv/bin/python scripts/check_archive_plan.py \
  --plan /path/to/archive_plan.json \
  --reusable-root /path/to/prototype-reusable-dataset \
  --output-dir outputs/compatibility-check
```

每筆均呼叫 `run_reusable.py` 的無模型 preflight，保存 manifest／archive check／logs。
未找到 archive、source mismatch 或解析錯誤都不會標成成功。`make_local_archive_plan.py`
僅重組本工作區既有實驗路徑；別台電腦應自行提供上述 plan，不依賴此工作區絕對路徑。

## 測試與限制

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/runtime_archive_smoke.py
.venv/bin/python tests/runtime_smoke.py
```

前者為單元測試；archive runtime 會真的編譯 synthetic Solidity fixture，再驗證不重新
編譯的 Falcon 載入、event/revert、global using/operator、Yul function lookup、tuple 與
兩個 overload 的精確 callers/callees。最後一項使用**明確的本機假模型**測試五種
成功／錯誤流程，不消耗訂閱額度，不能當成真實 dataset 檢測結果。

重要限制：TLOAD/TSTORE/MCOPY 使用與 Falcon 舊有 Yul builtins 相同的 opaque call 表示。
沒有新增完整 EVM memory／transient-storage alias analysis，不宣稱能偵測所有相關漏洞。
`ready_for_analysis` 不是 `completed`；本次沒有新增真實 predictions 或 Judge report。

# 共用 Reusable Dataset → GPTScan adapter

2026-11-05 的 dataset 相容性、舊 archive 模式與 compiler-context build 修正見
[COMPATIBILITY_20261105_ZH.md](COMPATIBILITY_20261105_ZH.md)。該更新保留 strict
archive 驗證，並在 archive 模式改用 compiler signature／Falcon resolved CallGraph；
下列 Java requirements 主要仍適用舊的 source-only 執行模式。

## 不是 Falcon 與 Crytic Compile 二選一

Falcon 本身使用 Crytic Compile。既有 Docker runner 輸出的 Crytic Compile archive
包含 source text、AST、bytecode、source map 和 compiler 資訊。
這個 adapter 讓 Falcon 直接載入同一份編譯結果，不再讓它猜 framework 或重新編譯。

```text
原始 dataset repo（read-only） + build.json
    ↓ 既有 Reusable Dataset Docker image / docker_repo_runner.py
setup → materialize entrypoint → compile → archive + provenance manifest
    ↓ 校驗 recipe / source commit / compiler settings / scope / SHA256
以 archive 的 embedded source 建立獨立、可攜的分析快照
    ↓ 重定位路徑，但不改 source、bytecode、AST IDs、source offsets
Falcon + Crytic Compile Archive loader（不重新編譯）
    ↓ 共用 compiled target inventory
GPTScan parser / CallGraph → price rules → Codex gateway → static checks
    ↓
output.json + prediction_case.json
```

目前**編譯在 Docker，GPTScan/Falcon/Java/model client 在本機 Python 3.10 環境**。
不是宣稱所有步驟都已移到 container。訂閱 OAuth credentials 也不會傳進 build container。

## 新接口

`scripts/run_reusable.py` 是建議入口；舊 `run_dataset.py` 保留作原始流程比較。
新模式預設只做 build/archive/Falcon/CallGraph preflight，**不消耗模型額度**。
實際三 repo 的完整測試結果與開發中失敗紀錄摘要見
[ADAPTER_VALIDATION_20261103.md](ADAPTER_VALIDATION_20261103.md)。

需要：

- 此 GPTScan fork 的 `.venv`，依 `requirements-fork.txt` 安裝（Python 3.10）。
- 可用的 Java 17+（`java -version` 必須成功）。
- Docker daemon，以及你已建好的 Reusable Dataset image。
- 可讀取的 Reusable Dataset checkout：需包含 `scripts/docker_repo_runner.py`、
  `src/build_scope.py`、`dataset/repos/<repo_id>/build.json` 和 candidate repo。
- 測試使用的 reusable checkout commit 為 `c95c1f7`，image tag 為
  `pmdetector-reusable:per-repo-final`。實際 image ID、runner/scope SHA256 會寫入 run manifest。
  image tag 本身不是永久固定內容的保證；重現請對照 manifest 的 digest。

### 先做不呼叫模型的檢查

```bash
source .venv/bin/activate
python scripts/run_reusable.py \
  --reusable-root /path/to/prototype-reusable-dataset \
  --repo-id 2023-06-real-wagmi \
  --image pmdetector-reusable:per-repo-final \
  --output-dir outputs/wagmi-ready
```

`--repo-path`、`--build-json` 可以覆寫來源位置，但 HEAD 必須符合 build.json 的 ref。
原始 repo 掛載為 read-only；build 在 container 的副本執行。輸出目錄必須新建，不覆寫舊結果。
build 的 setup/compile 指令來自**你信任的** build.json；只對可信 repo/config 使用此功能。

`--build-timeout-minutes` 預設 30 分鐘，與模型分析的時間預算分開。
build output 與 sidecar 預設留在 `.local/reusable-builds/<repo_id>/`，供下次驗證後重用。
Docker 的 compiler/npm 等 cache 預設使用 `pmdetector-reusable-cache` volume。
沒有自動啟動 taint analysis，也沒有啟動原專案的 LLM downstream。

### 以相同 archive 執行完整 GPTScan

```bash
python scripts/run_reusable.py \
  --reusable-root /path/to/prototype-reusable-dataset \
  --repo-id 2023-06-real-wagmi \
  --archive .local/reusable-builds/2023-06-real-wagmi/analysis_artifacts/2023-06-real-wagmi_export_archive.json \
  --run-analysis \
  --token-file /path/to/authorized/auth-gateway.token \
  --model openai-codex/gpt-5.6-luna \
  --timeout-minutes 30 \
  --output-dir outputs/wagmi-analysis
```

`--archive` 的 sidecar 及 build_result.json 應保留原位置，以便核對 build recipe、
effective Node version、source commit、compiler 與 scope。舊 archive 沒有新的 scope/provenance
資訊時會拒絕重用；需用既有 Docker runner 重建一次，不能為了 cache hit 跳過驗證。
若不指定 `--archive`，會呼叫既有 runner，它自己決定 warm archive cache 是否可重用。

讀取 archive 後，Falcon 的 loader 明確指定 `Archive` platform，沒有 compiler fallback。
單次呼叫只接受一個 Crytic Compile archive（可含多個 compilation units）；不默默合併
不明來源的多份 archives。原始 archive 不會被修改。

## 統一 scope，不手動搬走測試檔

Compiler input 排除政策沿用 reusable `production-v1`。adapter 再從**實際編譯過**的
source inventory 產生 `scope.json`：

- `compiled_sources`：Falcon 可以使用的完整編譯上下文。
- `target_files`：GPTScan 可回報的來源。
- `dependency_sources`／`excluded_analysis_files`：保留給 Falcon，但不當回報目標的依賴。
- `source_files_sha256`：分析快照的檔案必須與 archive embedded text 相同。

`node_modules`、`lib`、`external`、`openzeppelin`、`uniswap`、`pancakeswap`、`legacy`
等依賴目錄，以及 compiler 標示的 dependencies，不當成 report targets；這項 policy
另記為 `gptscan-production-v1`。這會影響分析覆蓋範圍，不能宣稱所有 repo 內檔案都被檢測。
未來若要分析這些依賴，應明確擴展 policy 並處理 overload，而不是靜默納入。

Parser 直接依 scope.json 讀檔，不再用 `os.path.split()` 猜巢狀 test 路徑；CallGraph 的
可分析集合也裁到同一份 target inventory。Preflight 會要求 parser contract 能唯一映射回
Falcon 的已編譯 contract，因此不再把未編譯的 test contract 送給 static checker。
正式 target 中若有尚未支援的 overload，仍明確失敗，不猜測目標。

## 兩項獨立的相容性修正

### Falcon bytecode API

`src/falcon_compat.py` 僅用於測試過的 Falcon 0.2.28 / Crytic Compile 0.3.3。
針對 `type(C).creationCode`／`runtimeCode`，以目前 compilation unit、宣告檔案和 contract
名稱找到唯一 SourceUnit，取得真正 bytecode。其他 IR 行為沿用原函式。
不修改 `.venv` 套件檔、不回傳假的空 bytecode，也不忽略 IR errors。

### Reusable cold dependency boundary

目前 checkout 的 runner 會把 npm install 後新增的 dependency Solidity inventory
誤認為 project source boundary 改動。`scripts/reusable_build_bridge.py` 只調整該 audit hook：

- 允許 `node_modules/`、`lib/` 的 dependency inventory 隨 setup 建立。
- 仍拒絕正式來源新增／刪除、scope policy/fingerprint 改變。
- 沿用原 setup/compile/archive 命令與 artifact 驗證，不跳過 scope archive validation。
- 不修改外部 reusable checkout，也沒有複製一份各 repo 的 build recipe。

這是 adapter 端明確記錄的兼容處理，不宣稱外部 runner 已修好。對非標準 dependency 位置
需額外定義和測試，不能一律放寬所有路徑。

## 輸出與完成條件

```text
adapter_manifest.json          # 分階段狀態、build/analysis 設定與 provenance
build.json                     # 本次 recipe 副本
build.log / build_result.json  # 既有 runner 的結果（若本次有執行 build）
input_export_archive.json      # 路徑重定位後的分析副本
scope.json                     # 共用 compiled/report-target inventory
source/                        # archive embedded source snapshot
archive_check.json / .log      # Falcon IR 與 parser/CallGraph preflight
output.json                    # 完整分析後才有的 native output
output.json.metadata.json
prediction_case.json
execution.log / model_events.jsonl
```

- `ready_for_analysis` 只代表 preflight 成功，**不是完整分析成功**。
- `completed` 代表完整 GPTScan 成功並有 PredictionCase。
- `failed`／`timed_out` 不可當成零 findings。
- scope、IR 或模型錯誤都不會輸出可假裝成功的 PredictionCase。
- findings 的 description/impact/mitigation 仍是 rule templates；沒有暗中改成 LLM enrichment。
- 此 adapter 不會執行 LLM Judge。仍需用既有 `validate_prediction.py` 驗證，再明確執行 evaluation。

完整測試另外修正兩個錯誤分類／格式問題：規則條件不成立是正常 negative candidate，
不是 infrastructure failure；static-variable JSON 若格式錯誤，最多要求模型重答一次。
不會把無效 JSON 當成 No、也不會自行補造變數或漏洞內容。重試仍失敗會回傳 failed。

## 自動化測試

```bash
python -m unittest discover -s tests -v
python tests/runtime_archive_smoke.py
```

第二個測試會真的編譯 synthetic fixture 一次；載入 archive 時攔截任何 subprocess，
確保不會重編譯，並核對 creation/runtime bytecode，確認巢狀測試檔不會滲入 target 集合。
不消耗模型額度。GitHub CI 也包含這個測試。

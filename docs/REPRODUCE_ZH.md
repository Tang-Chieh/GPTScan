# GPTScan：Price Manipulation + Codex Gateway + PredictionCase

這是 `GPTScan/GPTScan` 的正式 fork，保留 AGPL-3.0 與 upstream history。
`main` 保留 upstream；`price-manipulation` 是本次開發 branch。

## 修改範圍

1. **Dataset repo adapter**：`scripts/run_dataset.py` 直接接收既有 repo 路徑，不 flatten、
   不重切 SCAR chunks、不根據 ground truth 挑檔。巢狀 Hardhat/Foundry 專案可指定
   `--project-subdir`，或讀既有 `build.json` 的 `source.working_directory`。
   不會自動執行 build.json 的 setup/compile shell commands，也不會自動下載 dependency。
   Falcon 實際編譯仍可能在原 repo 產生 framework build artifacts。
2. **Model transport**：取代舊 ChatCompletion 固定 GPT-3.5/GPT-4 呼叫，預設送到
   loopback Codex OAuth gateway 的 Responses endpoint，指定
   `openai-codex/gpt-5.6-luna`。GPTScan 只讀 gateway bearer token；真正 OAuth 由 gateway
   管理。不是把 OAuth token 當 OpenAI API key。沒有 provider/model fallback。
3. **Price scope**：`src/profiles.py` 在分析前只載入 LP valuation 與新增 oracle-price 規則；
   system prompt 同步限定 price/oracle manipulation。不是通用掃描後再用關鍵字過濾。
4. **Output**：保留 native JSON，加上 parser 的 contract/function identity；直接匯出
   `PredictionCase`。沒有額外要求模型生成新 findings，也沒有讀取 ground truth。
5. **可靠性**：每 repo 獨立工作目錄；失敗/逾時不輸出可當成完成結果的 PredictionCase；
   malformed yes/no、缺少 scenario answer、無法唯一定位的結果都明確失敗。
   修正 upstream CallGraph 的 contract flag 與 property-rule index 對應錯誤。
   靜態檢查以 file+contract 縮小範圍，避免同名 function 落到另一個 contract。

## 安裝

建議使用 Python **3.10**（Falcon 的舊版依賴不保證支援最新 Python）、Java **17+**、
Git、以及各目標專案需要的 Node/npm/Foundry 等工具。

```bash
git clone --branch price-manipulation https://github.com/Tang-Chieh/GPTScan.git
cd GPTScan
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-fork.txt
python -m pip install pydantic==2.12.3  # 只供測試及 evaluator schema validation
java -version
solc-select install 0.8.19  # 範例，不是所有 repo 都用這版
```

Linux 安裝 pysha3 等舊依賴可能需要 C compiler/Python headers；Java 需自行安裝。
如果 Solidity binary host 回傳 403，應修正網路或改用官方 Solidity GitHub release 的
對應 binary，不要跳過編譯或將編譯失敗算成無漏洞。
實際目標 repo 的 framework/dependency/compiler 應先根據原有 build.json 準備。
這次沒有實作通用的 build.json executor，也沒有保證 Crytic archive 能直接給 Falcon 用。

## 訂閱模型連接

可沿用 Hound/SmartAuditFlow 已授權的本機 gateway；token 檔只指定路徑，**不要上傳**。
先前已登入不代表永久有效；401、403、額度不足時需在 gateway 重新授權或等待額度恢復。
不要 fallback 到付費 API 或另一個模型。

若要在新機器建立獨立 gateway，本 repo 提供相同的 pinned OMP 18.6.0 wrapper：

```bash
python scripts/gateway.py install
python scripts/gateway.py auth-broker login openai-codex
python scripts/gateway.py auth-broker serve
# 另一個 terminal，保持 broker 運行：
python scripts/gateway.py auth-gateway serve --bind=127.0.0.1:4000
```

wrapper 將 credentials 放在忽略追蹤的 `.local/omp/`；native loader 可能另外使用
`~/.omp/natives`。它是第三方 OMP runtime，不是 GPTScan 原生或官方 OpenAI SDK。
gateway 啟動時會顯示 bearer token 的路徑，請使用該路徑：

```bash
python scripts/gateway_smoke.py \
  --token-file /absolute/path/to/auth-gateway.token
```

預設只允許 `http://127.0.0.1:4000/v1` 等 loopback；拒絕遠端 host、redirect 與環境 proxy，
避免將本機 bearer 外送。smoke 會真的消耗少量訂閱額度，測 yes/no 與 JSON 兩個請求。
這與直接使用 ChatGPT/訂閱授權的 eligibility/usage limits 有關，不能保證任意帳號有相同模型。
官方方案授權背景見 [Sign in with ChatGPT](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)。

## Dataset 如何成為 input

原有 dataset repo 不必複製進這個 fork。例如：

```text
candidate-repos/2023-06-real-wagmi/concentrator/
dataset/repos/2023-06-real-wagmi/build.json
```

先產生 input manifest，不呼叫模型、不編譯：

```bash
python scripts/run_dataset.py \
  --repo-id 2023-06-real-wagmi \
  --repos-root /path/to/candidate-repos \
  --build-json /path/to/dataset/repos/2023-06-real-wagmi/build.json \
  --output-dir outputs/wagmi-prepare \
  --prepare-only
```

真正執行時使用**新的 output 目錄**，並移除 `--prepare-only`：

```bash
python scripts/run_dataset.py \
  --repo-id 2023-06-real-wagmi \
  --repos-root /path/to/candidate-repos \
  --project-subdir concentrator \
  --token-file /absolute/path/to/auth-gateway.token \
  --profile price \
  --model openai-codex/gpt-5.6-luna \
  --timeout-minutes 30 \
  --output-dir outputs/wagmi-price-run1
```

`--repo-path /path/to/repo` 可以替代 `--repos-root`。
單一 solc 專案可加 `--solc-version 0.8.19`（必須已安裝）。多版本 framework 請使用其
原有設定，不能把整個 dataset 都指定成同一版。需要的 framework 環境變數由使用者設定；
runner 不自動採用 build.json 裡的任意 environment 或 commands。

每個 repo 的執行彼此獨立；要跑其他 repo，換 ID/path/build.json/output-dir。
不要以 Ground Truth 裡的 vulnerable function 選取 input。

## 執行流程與輸出

```text
Dataset repository → Falcon compilation + Solidity parsing/Java CallGraph
→ price-rule prefilter → GPT scenario/property matching
→ GPT key-variable extraction → original static confirmation
→ deduplication → native JSON + PredictionCase
```

成功目錄：

```text
output.json                    # Native results（保留，加上 identity/impact）
output.json.metadata.json      # compilation/analysis/rule counts；token/cost 未量測則 null
prediction_case.json           # 可送 benchmark evaluator 的 input
run_manifest.json              # repo/detector commit、dirty flag、input SHA256、模型、狀態
model_events.jsonl             # request completed/failed；不保存 credentials
execution.log                  # 原有分析 log，可能包含受測原始碼
work/                          # 每次獨立的 callgraph/dataflow 暫存
```

`prediction_case.json` 的 `description`/`impact`/`mitigation` 是**規則模板**；
`mitigation` 對應 recommendation；不是人工讀 GT 後補上，也不是額外 LLM 寫報告。
`report_basis` 明確標示此限制。沒有空字串或 `Not provided...` 的假填值。
general profile 的 impact 若無專用模板，會使用原規則 description，品質較受限。
這次實作的是 price profile，不宣稱已重現原論文模型或 general baseline 的數據。

`--timeout-minutes` 是整個 repo 的 wall-clock 上限，不是完成覆蓋率保證。
compile/analysis/model 錯誤回傳非零退出碼，`run_manifest.status` 為 failed/timed_out；
partial output 不可當作已完整掃描。native `success` 不是完成依據，請看 run_manifest。
原有篩選規則可能排掉某些程式，即使 completed 也不代表全 repo 漏洞覆蓋率 100%。

## LLM Judge 接口

先用我們**實際 evaluator 的 schema**驗證，而不是只看 JSON 長得像：

```bash
python scripts/validate_prediction.py \
  --contract-file /path/to/prototype/src/benchmark_eval/contract.py \
  --prediction outputs/wagmi-price-run1/prediction_case.json
```

成功後，把每個成功 repo 的 prediction_case.json 複製為獨立資料夾內的 `<repo_id>.json`，
再按該版 `src/benchmark_eval/README.md` 執行 OAuth/smoke/full evaluation：
`--predictions-dir` 指向該資料夾。不要把 metadata 或 partial JSON 一起放進 predictions-dir。
LLM Judge 的程式和 ground truth 不包含在本 fork；這次沒有執行完整 Judge、沒有產生
新的 benchmark `report.md`，也不宣稱任何 recall/precision。

## 已知限制

- 只覆蓋目前兩個 price patterns；不是所有 price manipulation 的完整 detector。
- Static dependency 並非完整 exploit proof；oracle 可操控性、驗證機制及跨合約狀態仍可能誤判。
- Upstream parser/callgraph 主要以 function name 索引。相同 contract 的 overload 目前會
  fail closed；不同 contract 的同名 caller resolution 仍是近似，不是完整 cross-contract analysis。
- Upstream 對 test/vendor/external/lib、短函式、白名單與 modifier 的排除保留。
  因此不應把「讀到 repo」解釋成「所有 function 都已評估」。
- Falcon、compiler/framework 相容性需逐 repo 驗證；沒有預先宣稱 23 個都能跑。
- template report 的 I/M 描述較籠統，可能影響 Judge 分數；不應將格式相容視為語意品質相同。

## 本次驗證

見 [VALIDATION.md](VALIDATION.md)。Unit tests 不消耗額度：

```bash
python -m unittest discover -s tests -v
```

GitHub CI 執行 adapter/transport/exporter unit tests，不是 23-repo benchmark。

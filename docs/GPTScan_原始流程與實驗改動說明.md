# GPTScan 原始流程與本次實驗改動說明

日期：2026-11-05。本文依原版 GPTScan、本機 `price-manipulation` branch 及本次實驗實際程式碼整理；不表示所有變更已推送 GitHub。

> 歷史實驗說明：2026-11-06 已將目前規則改為七條原版規則並刪除 OraclePrice，詳見 [規則調整說明](RULE_SELECTION_20261106_ZH.md)。本文的兩條規則與 23-repo 結果描述的是 11/05 舊實驗，不是調整後重新執行的結果。

> 輸出也已更新：`-o` 現在直接產生 `PredictionCase`，不需要先寫原生 JSON 再轉檔；目前行為見 [直接輸出說明](DIRECT_JUDGE_OUTPUT_ZH.md)。

## 1. 總結

本文說明 GPTScan 的原始分析流程，以及本次實驗的接入方式與程式改動。

我們保留 GPTScan「規則篩選 → LLM 判斷程式性質／擷取變數 → 程式分析檢查 → 合併 findings」的主架構，改動分成四部分：

1. **Dataset 接入**：重用 Reusable Dataset 的 Docker 編譯環境與 Crytic Compile archives，讓 Falcon 不必重新猜 framework 或重新編譯。
2. **模型連接**：讓 GPTScan 的模型請求經本機 gateway 使用已授權的 Codex 訂閱模型，而不是原版 API-key 連接方式。
3. **Price focus**：分析前只載入兩條價格相關規則，加上 price/oracle manipulation 的 system prompt 限制。
4. **輸出接入評估**：保留 GPTScan 原始 `output.json`，在工具執行結束時另外匯出 `prediction_case.json`，供正式 LLM Judge 使用。

本次成功集為 23 個 repo、204 筆候選 findings；後續以我們專案的 42 筆 gold-verified ground truth 做 Judge 評估。**

## 2. GPTScan 原始流程

### 2.1 原始 input 與環境

原版 CLI 使用 `-s` 指定 Solidity 專案來源位置、`-o` 指定輸出、`-k` 提供 OpenAI API key。

README 建議使用專案資料夾；單一 Solidity 檔案也建議放進資料夾再指定該資料夾。它不是只能讀一段 function，也不是必須先把 repo flatten 成單一 `.sol`。

原版支援部分 framework 專案，包括 Hardhat、Truffle、Brownie；但 repo 必須處在可被 compiler/framework 正確處理的狀態。使用者需自行準備相容的 solc、Node.js、依賴與 framework 設定。README 也提醒其路徑篩選較簡單，某些路徑名稱可能造成空輸出。

```text
使用者準備 compiler／framework／dependencies
    ↓
指定 Solidity 專案來源資料夾
    ↓
Falcon 編譯並建立程式分析模型
    ＋ source parser／CallGraph 解析函式與呼叫關係
    ↓
載入原本的漏洞規則集合
    ↓
依規則中的函式／內容特徵縮小候選
    ↓
LLM 判斷候選 function 是否符合規則描述的 scenario／property
    ↓
需要時取得 caller context，再判斷組合情境
    ↓
LLM 擷取該條規則要求的變數
    ↓
執行指定 static checker，例如 data dependency
    ↓
合併 findings，輸出原生 JSON 與 metadata
```

這不是「LLM 自由閱讀整個 repo 後直接撰寫完整 audit report」。規則定義了要問的問題與要做的程式檢查；LLM 和程式分析各自負責部分工作。

### 2.2 為什麼原版需要 compile？

因為 GPTScan 不只做文字比對，還會使用 Falcon 的程式分析模型檢查資料相依性等條件。這需要 compiler 產出的 AST 等資訊，以及正確的 import 與型別上下文。

原版在編譯失敗時可以繼續部分流程，但會警告精確度與召回率可能下降；我們的正式 dataset runner 使用 strict 模式，不把缺少必要程式分析能力的執行當成完整成功。

## 3. 我們如何處理 repo 編譯與 GPTScan input

### 3.1 build.json 的角色

`build.json` 是每個 repo 的 build recipe／設定，不是編譯完成的 Solidity 檔案，也不是所有依賴本身。

內容包括 repo 身分與固定 source ref、專案位置、framework／toolchain、setup／compile 步驟、必要的檔案 materialization、分析 artifact 位置及 scope 等設定；實際欄位依既有 schema 與 recipe 而定。

Docker image 提供工具環境；runner 讀取 recipe，在工作副本上安裝／準備依賴與執行編譯。**不是有一份 build.json 就自動保證任何分析器都能讀取其產物。**

### 3.2 編譯與接入流程

```text
原始 dataset repo + build.json
    ↓
Reusable Dataset Docker runner
setup／dependencies → framework compile → archive export
    ↓
Crytic Compile archive
source text／AST／bytecode／source maps／compiler 資訊
    ↓
共用 adapter：驗證來源、scope、archive，建立獨立 source snapshot
    ↓
Falcon 直接載入 archive，不重新 compile
    ↓
GPTScan 的 parser／CallGraph／rule analysis
```

關鍵區分：**Crytic Compile archive 是編譯產物的保存格式；Falcon 是分析器，能透過相容介面讀取該 archive。兩者不是互斥的 compiler。**

本次最終模型分析重用了已驗證的 archives，沒有在每次 GPTScan 補跑時重新編譯全部 repo。編譯準備在 Docker；GPTScan／Falcon 模型分析與 gateway client 在本機執行，LLM 推論由遠端模型服務執行。

### 3.3 Adapter 實際做了什麼？

| 部分 | 原本可能遇到的問題 | 本次處理 |
|---|---|---|
| Archive input | 原版 CLI 主要讓 Falcon 直接處理 source project | 新增明確 archive + scope 入口，讓 Falcon 讀既有產物 |
| 來源驗證 | 無法確認拿到的 archive 是否對應這個 repo 版本 | 檢查 source ref、內容、recipe／sidecar、雜湊等；驗證項目依 strict／legacy 模式區分 |
| 舊 archive | 舊產物沒有新版 provenance sidecar | 明確 `--legacy-archive`，比較 embedded source，記錄缺少完整 build provenance；不冒充完整驗證 |
| 分析路徑 | 容器絕對路徑無法直接在本機使用 | 從 embedded source 建 snapshot、重定位路徑，保留 source bytes 與定位對照 |
| 編譯範圍與回報範圍 | 過早移除依賴會破壞 framework compile | 保留必要 compiler context，再依 scope／production roots 與 import closure 決定分析範圍 |
| Overload／同名 contract | 只靠 function name 可能定位錯誤 | 使用檔案、contract、完整 signature、compiler source location；archive 模式使用 Falcon resolved calls |
| Falcon 相容性 | 新 AST／Solidity 特性在舊版 Falcon IR 轉換出錯 | 增加限定版本的 compatibility 層與 regression tests，不修改 site-packages 或原始 repo |

主要實作：`scripts/run_reusable.py`、`src/reusable_archive.py`、`src/archive_scope.py`、`src/antlr4helper/callgraph.py`、`src/falcon_compat.py`、`src/static_check.py`。

部分 framework 必須保留更完整的原始編譯上下文，另有 `scripts/build_compiler_context.py` 與 Brownie compiler capture／export 工具。這不代表完全沿用原本 pre-build pruning；manifest 會記錄實際 policy，不能把 compiler-context build 說成已通過另一套 scope policy。

這些接入修正不只是 JSON 格式改動，也不是可以保證任意未測試 repo 都成功的通用轉換器。Falcon compatibility 層仍有版本與分析能力限制，例如部分新 EVM builtins 只有 opaque call 表示，不是完整的 memory／transient-storage alias analysis。

## 4. 如何讓 GPTScan focus on price manipulation？

我們不是先跑完 general audit 再刪掉不相關 findings，而是在**分析前的 rule selection 與模型指令**限制範圍。

### 4.1 原版與修改版對照

| 項目 | 原版 | 本次 price profile |
|---|---|---|
| 載入規則 | `load_all_rules()` 掃描規則資料夾中的 `.yml` | `src/profiles.py` 明確只選 `Flashloan_Price.yml`、`OraclePrice.yml` |
| System prompt | 通用 smart contract auditor、回答 code properties、遵守格式；原文另要求在背景模擬多次回答 | 調整基礎指令，加入不信任 source comments 的限制，price 模式再加專門範圍指令 |
| 原有 price rule | 已有 LP token price/value manipulation 規則 | 保留原有 scenario、變數擷取與 data-dependency checker；補 impact、調整 recommendation 模板 |
| Oracle／金融操作 | 沒有我們新增的這條 OraclePrice 規則 | 新增 attacker-influenceable price → financially sensitive operation 的候選規則 |
| 輸出範圍 | 所載入規則可產生的 findings | 只來自上述兩條規則；不宣稱涵蓋所有 price manipulation 類型 |

這不是只改了一句 prompt；但也沒有把 GPTScan 改成不同的多 agent 方法。原版與修改版的模型、system prompt、規則集合、接入與錯誤處理均有差異，不能宣稱完全等同原版 benchmark。

### 4.2 System prompt 具體新增的範圍

位置：`src/chatgpt_api.py` 的 `PRICE_SCOPE`，price profile 下由 `Chat.sendMessages()` 加入每次請求。

```text
Focus only on price/oracle manipulation: attacker-influenceable reserves,
balances, liquidity, spot prices, exchange rates or protocol state affecting
asset valuation or financial operations. Price-related names alone do not
establish vulnerability. Consider existing validation and manipulation resistance.
Do not report unrelated access control, reentrancy or generic bugs.
```

意思是：關注攻擊者可影響的價格／儲備／餘額／流動性／匯率或狀態，如何影響估值與金融操作；不能只因為名稱包含 `price` 就認定漏洞，也要考慮既有驗證措施。

注意：與價格漏洞直接相關的 access control 仍可能是漏洞機制的一部分；指令排除的是**不相關**的通用問題，不是宣稱所有 access-control 問題一律無關。

### 4.3 兩條實際規則

**A. `Flashloan_Price.yml`（既有規則）**

- 判斷函式是否取得／計算 LP token value/price，並依賴 reserves、AMM price、exchange rate、balance／supply 等資料。
- 內容特徵包括 `getPrice`、`exchangeRate`、`totalSupply`、`balanceOf`、`getReserves` 等；這只是候選篩選，不是漏洞證明。
- LLM 擷取 `VariableA`（市場／餘額等輸入）與 `VariableB`（LP 估值輸出），再交 `find_data_dependency`。
- 本次未把這條規則重新設計成自由式 LLM audit；主要新增 impact 與修改 recommendation 的輸出文字。

**B. `OraclePrice.yml`（新增規則）**

第一個 property：從 DEX spot state、reserves、token balances 或其他 attacker-influenceable protocol state 推導價格、匯率或資產估值。

第二個 property：該數值用於 borrowing、minting、redeeming、withdrawing、liquidation、swaps 或 rewards，且缺乏足夠獨立／time-weighted validation。

- 特徵含 `slot0`、`getReserves`、`balanceOf`、`getPrice`、`latestAnswer`、`latestRoundData`、`exchangeRate`、`price`、`reserves`。
- LLM 擷取 `VariableA`（可能受攻擊者影響的 pricing input）與 `VariableB`（金融操作使用的估值或數量）。
- 使用原有 `find_data_dependency` checker，不是新增完整 flash-loan simulation、oracle robustness proof 或經濟攻擊驗證器。

因此，**price focus 是定向候選偵測，不是確保每個結果都已證明可操縱或可獲利。**

## 5. 模型連接與執行保護

### 5.1 API key → 授權的本機 gateway

原版 `src/chatgpt_api.py` 直接呼叫 OpenAI ChatCompletion，使用 API key 與原本設定的 GPT-3.5／GPT-4。

本次保留模型問答的 string-in／string-out 介面，將傳輸抽到 `src/model_transport.py`：

```text
GPTScan 問題與程式片段 → 本機 loopback gateway → 已授權的 Codex 模型 → 回覆文字
```

本次 detector 使用 `openai-codex/gpt-5.6-luna`。本機 token file 只在執行時讀取；登入憑證不寫入 dataset bundle、PredictionCase 或文件。原版 API mode 仍可明確選擇，不會在訂閱模式失敗時偷偷切到 API key 或其他模型。

### 5.2 Woofi 與 ParaSpace 補跑

| 問題 | 實際修正 | 未改什麼 |
|---|---|---|
| Woofi JSON reply 不符合預期 | OraclePrice 找不到變數時統一回 `{}`，不要求 `N/A` 字串；格式重試包含 key/type 與驗證原因 | 不捏造變數、不把無效 JSON 當成陰性結果；原失敗回覆未完整保存，因此不能證明只有這個原因 |
| ParaSpace 單次模型問答逾時 | 新增 `--request-timeout-seconds`，最終補跑設 180 秒，同步 transport timeout | 不修改候選判定或漏洞分數；預設 wall timeout 仍 90 秒 |
| Repo 總時限 | 原批次 30 分鐘；三個未完成 repo 補跑 60 分鐘 | 與單次模型問答 timeout 分開；不是 GPTScan 原版要求整個 repo 只能跑 30 分鐘 |

另有 strict error tracking：真正的模型／分析錯誤不當成「零漏洞」；但規則條件不成立應是正常 negative candidate，而不是 infrastructure failure。JSON 格式最多要求模型重答一次，仍無效則失敗。一次失敗後停止後續模型請求的保護屬於我們新增的行為，不是原版設計。

## 6. GPTScan output 如何成為 LLM Judge input？

### 6.1 不是要求模型直接生成整份 PredictionCase

本次採用的是：

```text
GPTScan rule analysis 結果
    ↓ utils.convert_output()
原生 output.json
    ↓ src/prediction_export.py 的 deterministic exporter
prediction_case.json
    ↓ schema validation
正式 benchmark_eval → LLM Judge → report.md
```

Exporter 由 `src/tasks.py` 在分析成功後呼叫，透過 `--prediction-output` 指定位置。它是工具內整合的**程式轉換層**；不是額外人工閱讀結果，也不是另一個 LLM enrichment 步驟。

### 6.2 欄位對照

| Judge input 欄位 | 資料來源／處理 |
|---|---|
| `repo_id` | runner／CLI 的 repo identity |
| `detector_metadata.detector_version` | price 模式記為 `gptscan-price-v1` |
| `detector_metadata.llm_model` | 實際指定的 detector model |
| `predictions` | 原生 `output.json.results` 的每筆結果 |
| `finding_id` | repo_id、rule code、locations 的穩定雜湊；不是複製 ground-truth ID |
| `title` | 規則 output title |
| `description` | 規則 output description |
| `impact` | 本次在 price rules 新增的 output impact 模板 |
| `mitigation` | 規則 `recommendation` 映射為 `mitigation` |
| `vulnerable_code.file` | affectedFiles 路徑轉回 repo-relative logical path |
| `vulnerable_code.contract`／`function` | 已解析的 contract 與 function signature；原生輸出處增加對應資訊 |
| `start_line`／`end_line` | 原生 source range；檢查為有效、由 1 開始的 inclusive 行號 |
| 額外 provenance | `severity`、`rule_id`、`report_basis`；標明 rule-template、非 exploit proof |

`src/utils.py` 也有調整：原生輸出攜帶 impact 與較精確的 contract／function identity，供 exporter 使用。

### 6.3 impact／mitigation 是誰寫的？

**是開發時寫在規則 YAML 裡的通用模板，不是 LLM 對每一筆 finding 個別生成，也不是人工逐筆補寫。**

例如 OraclePrice 的 mitigation 模板是建議使用 manipulation-resistant oracle／validated time-weighted price，並檢查 freshness、deviation 與 transient state。

Exporter 只搬移／驗證欄位，不判斷這段建議是否真的能修復該筆漏洞；是否具體、是否正確，要由後續 Judge 的 mitigation 分項評估。**字串非空不代表 mitigation 有足夠實質內容。**

它不讀取 ground truth 補寫 finding；ground truth 只在獨立評估階段使用。

### 6.4 為什麼要保留兩份輸出？

- `output.json`：保留 GPTScan 的原生 finding 結構，方便查核與對照。
- `prediction_case.json`：相同結果經 deterministic mapping，符合共同評估格式。
- 模型／分析失敗不輸出可假裝完整成功的 PredictionCase；合法零結果可輸出 `predictions: []`。
- Exporter 對缺少必要文字、越界路徑、無效行號或缺失 location 會報錯，不補造內容。

## 7. 本次 23 Repo 的最終資料與 Judge

| 項目 | 結果 |
|---|---:|
| 成功執行並通過 PredictionCase 驗證的 repo | 23／23 |
| 候選 findings | 204 |
| 評估 ground-truth findings | 42 |
| 達到配對門檻並被 matching 採用的 predictions | 26 |
| Pooled soft precision | 0.0853 |
| Pooled soft recall | 0.4143 |
| Pooled soft F1 | 0.1415 |

Judge 使用專案既有 `src/benchmark_eval`，不是 GPTScan 自帶的評估器。版本快照為 SCAR commit `e46fc2702a1c6506f9a56af00990f8218648f697`；使用 OAuth、`gpt-5.6-luna`、`end-to-end-v2`，以 R／L／I／M 分項評估，包含 root cause、localization、impact、mitigation。

這些是 soft／加權指標，不能把 soft recall 直接當成命中筆數比例。26 是匹配採用的 prediction 數，不是 204 筆皆經過獨立 exploit 驗證。

解讀限制：

- 完成集混合原批次與補跑：多數 repo 30 分鐘，三個補跑 60 分鐘；ParaSpace 最終單次請求為 180 秒，其他為 90 秒。
- 三個補跑使用修正後 JSON prompt，不能宣稱所有 repo 完全同版本／同預算重跑。
- Sentiment 零候選、未進入模型問答；Telcoin 有模型分析但零 findings。兩者都不是安全證明。
- 分析範圍由 archive／scope 決定；不等於 repo 所有檔案都完整覆蓋。
- 原始資料與 GPTScan 分析不需要 ground truth；評估才載入 ground truth。

## 8. 檔案位置

在 GPTScan 專案根目錄下：

```text
docs/GPTScan_原始流程與實驗改動說明.md       本文件
scripts/run_reusable.py                      Docker／archive → GPTScan 入口
src/chatgpt_api.py                           基礎與 price system prompt
src/profiles.py                              price／general 規則選擇
src/rules/Flashloan_Price.yml                 既有 LP price rule 與輸出模板
src/rules/OraclePrice.yml                     新增 oracle／price manipulation rule
src/prediction_export.py                     PredictionCase exporter
scripts/validate_prediction.py               格式驗證
outputs/dataset-23-consolidated-20261105/
├── README.md                                23 repo 結果總表
├── consolidated_results.json                23 repo 完整資料與來源紀錄
├── predictions/<repo_id>.json                Judge 的逐 repo inputs
├── EVALUATION_RUN.md                         評估設定
├── evaluator_source/                        評估器與 ground-truth 快照
└── llm_judge/
    ├── manifest.json
    ├── judge_artifact.json
    ├── report.json
    └── report.md                            最終正式評估報告
```

## 9. 對外簡短說法

> 我們以 Reusable Dataset 的 Docker build recipes 產生並驗證 Crytic Compile archives，透過共用 adapter 讓 GPTScan 的 Falcon 直接讀取編譯結果。分析前選用 LP valuation 與 oracle-price manipulation 規則，並加入 price-focused system prompt；模型請求走授權的本機 Codex gateway。工具保留原始 JSON，另外以 deterministic exporter 產生 PredictionCase，再交由既有 LLM Judge 與 gold ground truth 比對。Findings 的 impact／mitigation 是規則模板，並非逐筆 LLM 生成的 exploit 或修補說明。

對照基準：本機保存的 upstream/main commit `29a174773bd526c32ab7d6a8c78a63870330ccc7`；本文也包含後續尚未 commit 的 JSON、timeout 與彙整修改。未更動 GitHub、未新增 commit／push。

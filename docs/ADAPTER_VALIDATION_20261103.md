# Reusable Dataset 共用 adapter：實測紀錄

日期：2026-11-03，Asia/Taipei。這是開發期間的整合測試，**不是固定版本的正式 benchmark**。
沒有讀取 Ground Truth、沒有跑 LLM Judge、沒有計算 precision/recall。

## 核心結果

三個 repo 都能重用 Reusable Dataset 的 Docker 編譯流程與 archive，通過 Falcon IR、
正式來源 CallGraph、GPTScan price analysis，並產生符合現有 evaluator schema 的 PredictionCase。
原始 Reusable Dataset checkout 和 candidate Solidity 合約沒有被 adapter 修改；
原始 repo 在 build container 中 read-only 掛載，不再手動移走 Olympus 測試目錄。

| Repo | 最終 attempt | 分析 commit | 完成模型請求 | Findings | 分析錯誤 | 分析耗時（不含初次 Docker build） |
|---|---|---|---:|---:|---:|---:|
| 2021-07-spartan | spartan-full-v2 | 08cdf9d | 161 | 13 | 0 | 482.90 秒 |
| 2023-03-olympus | olympus-full-v2 | 3e93015 | 25 | 1 | 0 | 70.71 秒 |
| 2023-06-real-wagmi | wagmi-full-v3 | 709fe89 | 109 | 10 | 0 | 366.66 秒 |

三個最終 runs 啟動時 detector worktree 都是 clean。個別修正分開 commit；
model/schema/infrastructure 的問題逐步修復，因此各 run 的 commit 不完全相同。
若要正式比較其他工具或跑全 dataset，應先凍結最新版本與設定，再統一重跑。
不能把開發重試後的 findings 數當作 recall 提升或漏洞已確認。
模型輸出本身也可能變動；先前 Olympus 的 2/3 筆診斷 runs 都保留，不拿來取代最新成功 run。

## Archive 與 scope preflight

| Repo | Falcon contracts（含必要依賴） | Parser files | Parser retained functions | IR errors |
|---|---:|---:|---:|---:|
| Spartan | 25 | 26 | 139 | 0 |
| Olympus | 47 | 20 | 55 | 0 |
| Real Wagmi | 39 | 14 | 27 | 0 |

Parser files/functions 是原有 empty-function／whitelist 等篩選後的 inventory，
不代表每個 function 都送過模型，也不是 repo 的 100% 漏洞覆蓋率。
Dependencies/vendor context 保留給 Falcon，但不一定屬於 report targets，詳見 scope.json。

逐一比較原始與重定位後的 archive：三個 repo 的 embedded source text 都未改動；
25 / 47 / 39 個 contracts 的 ABI、creation bytecode、runtime bytecode、source maps、
libraries 資料全部一致。只修改 portability 所需的 metadata 路徑。

## Docker cold/warm reuse

- 使用既有 `pmdetector-reusable:per-repo-final`，實際 image ID：
  `sha256:9f007da176c2a3ae7e345510b1850968245f9a9cc8a33d64aec92a2aa24bc644`。
- 外部 reusable checkout：`c95c1f7`；runner/scope module SHA256 保存於 adapter_manifest。
- Compiler、framework、setup、materialized entrypoint 都由原 build.json + runner 處理。
- 三個 repo 的 warm 驗證均為 archive cache **hit**，build_result 的 `commands` 都是 `[]`。
  沒有再次執行 setup/compile/archive export。
- Falcon 明確以 Archive platform 載入；不是在背景又跑一次 framework compile。
- Host 的 Falcon/Java 分析環境與 Docker 的 build 環境分開，詳見 REUSABLE_ADAPTER_ZH.md。

## 實際暴露的問題與修正

1. **Falcon/Crytic bytecode API**：以 exact source unit 取得 creation/runtime bytecode，
   消除 Real Wagmi 的 API 不相容；不返回假的空 bytecode。
2. **Compiler/parser scope 漂移**：以已驗證 archive 的 compiled target inventory 取代
   GPTScan 的巢狀路徑猜測，測試檔不再混進靜態檢查。
3. **Reusable cold dependency audit**：在獨立 bridge 容許 node_modules/lib 依賴安裝產生
   的 inventory，不允許正式來源邊界或 policy 改變；未修改外部 checkout。
4. **候選淘汰誤判成執行錯誤**：原規則 `validate_description`／`exclude_variable` 的
   negative predicate 現在是 CandidateRejected，不再中斷整個分析。
5. **Model JSON 格式錯誤**：加入最多一次格式重試；不修補內容、不填假 finding，
   兩次仍不合格則整體失敗。最終 Real Wagmi v3 本身沒有觸發 format retry，
   所以不能宣稱該成功 run 一定是由 retry 救回；retry 的行為由 deterministic regression 驗證。
6. **Docker image reference**：先核對本機 reference 對應唯一 image ID，再固定 ID 執行，
   避免 image-store tag inspect 問題；不改用其他 image，也不自動 pull。

中途失敗的 attempts 都保留；失敗 runs 沒有被當成 0 findings 或成功完成。
每個修正各自 commit，可獨立 review，不用修改 dataset 合約來遷就工具。

## 測試

- 30 個 unit tests 通過。
- 真實 compiler/Java + fake-model runtime：positive、negative、malformed、rule rejection、
  一次無效 JSON 後成功 retry 的五種狀況通過。
- Archive runtime：先真實編譯 fixture，再禁止 loader 啟動任何 subprocess；成功取得
  exact creation/runtime bytecode，且巢狀測試檔不進 parser。
- 真正 reusable runner 的 provenance checks：有效 archive 接受，SHA 被改、source commit
  不符、即使更新 SHA 後仍混入 excluded test source 的情況都拒絕。
- 三份最終 PredictionCase 都用現有 `scar-e46fc270/src/benchmark_eval/contract.py`
  的實際 Pydantic model 驗證通過。這是 schema validation，不是 LLM Judge 評分。

## 本機結果

結果根目錄：`outputs/reusable-adapter-20261103/`（忽略 Git 追蹤，沒有上傳 credentials 或原始碼快照）。

- 最終 outputs：`spartan-full-v2/`、`olympus-full-v2/`、`wagmi-full-v3/`。
- 每個目錄：prediction_case.json、native output、metadata、execution log、scope、
  archive_check、adapter_manifest、embedded source snapshot。
- Warm build：`spartan-warm-verified/`、`olympus-warm-verified/`、`wagmi-warm-verified/`。
- Provenance 負向驗證：`provenance_checks.json`。
- Docker archives/sidecars：`.local/reusable-builds/<repo_id>/analysis_artifacts/`。

尚未證明其餘 repos 全部相容；正式 target 的 overload、其他 compiler/IR 特性、依賴來源位置
或模型格式仍可能需要共用層級的支援。不可把本次 3 個成功案例推論成整個 dataset 已完成。

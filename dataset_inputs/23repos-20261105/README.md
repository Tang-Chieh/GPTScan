# 23 個 Dataset repo：可供 GPTScan 載入的 archive inputs

這份 bundle 保存修正後驗證過的 **23 份 Crytic Compile archive、對應 build.json、
source commit 與 preflight 摘要**。不是只有表格，也不是 23 個 repo 的完整 Git clone。
Archive 內嵌編譯所使用的 Solidity source、AST、bytecode、source maps；原始 bytes
以 gzip 壓縮保存，約 45 MiB，解壓約 406 MiB，不需 Git LFS。

**23/23 的通過代表 archive → Falcon IR → parser／函式定位 → CallGraph 成功，
不是全部跑完 GPTScan 模型分析。沒有包含本次新增 findings、LLM Judge 或 report.md。**

封裝解壓後已重新驗證 23/23 通過，見 [結果總表](RESULTS.md) 與
[checksum／code snapshot 驗證紀錄](ROUNDTRIP_VALIDATION.json)。

## 包含哪些檔案

```text
manifest.json                   # repo URL/ref、archive/build/sidecar SHA256、載入模式
<repo_id>/
  archive.json.gz               # 原始編譯 archive，解壓後逐 byte 相同
  build.json                   # 對應的原始 recipe
  preflight.json               # 解析結果與限制，去除本機工作路徑
  archive.manifest.json        # strict 模式的原始 sidecar（16 個）
  toolchain.json               # strict 模式所需的舊 build_result.toolchain 摘錄
  UPSTREAM_*                   # 原始 repo 可找到的頂層授權／notice
```

7 個明確採 source-compared 模式：MarginSwap、2021-08-notional、Blueberry、USSD、
Dopex、Abracadabra、2025-12-panoptic。這些不是冒充具有新版 sidecar attestation；
解壓後仍使用 `--legacy-archive`，並核對原始 repo／recipe。

沒有 OAuth token、gateway auth database、登入紀錄、`.git` 或重複的分析工作目錄。
Build recipe 的 `offline-build`、固定 dummy private-key 等是既有離線編譯佔位值，
不是登入憑證或可用的 API key；不要把這些公開測試值拿去保管資產。

## 1. 準備程式環境與原始 repo

在此 GPTScan fork 的 Python 3.10 `.venv` 安裝 `requirements-fork.txt`。
另需既有 Reusable Dataset checkout（驗證版本 `c95c1f7`，包含
`scripts/docker_repo_runner.py` 與 `src/build_scope.py`）。

把各 repo 放在該 checkout 的 `candidate-repos/<repo_id>`，並 checkout 到
`manifest.json` 的 `source_commit`。學長已經有正確版本的 repo 就不必重下載。
`repository_url` 與 commit 都有記錄；不需要為了分析 archive 再 npm install／重新編譯。

此 bundle 不包含 Docker image 或整個 Reusable Dataset checkout。
使用以下既有 archive 路徑時不會啟動 Docker；只有要重新建置時才需要 Docker。

## 2. 解壓與驗證 checksum

在 GPTScan 根目錄：

```bash
.venv/bin/python scripts/unpack_dataset_inputs.py \
  --bundle dataset_inputs/23repos-20261105 \
  --output-dir outputs/bundle-inputs
```

輸出目錄必須是新的；不覆蓋舊資料。會驗證 gzip、archive、build、sidecar 與
toolchain 的 SHA256，再產生適合目前電腦的 `outputs/bundle-inputs/archive_plan.json`。
GitHub 內的 manifest 不依賴我的 `/Users/...` 本機路徑。

## 3. 全部 repo 跑不呼叫模型的接入檢查

```bash
.venv/bin/python scripts/check_archive_plan.py \
  --plan outputs/bundle-inputs/archive_plan.json \
  --reusable-root /path/to/prototype-reusable-dataset \
  --output-dir outputs/bundle-preflight
```

預期 `summary.json` 的 23 筆狀態都是 `ready_for_analysis`。每個 repo 都有
manifest、archive_check 與 logs；這一步不呼叫模型、不跑 Judge。
Source commit／source bytes 不一致會明確失敗，請勿將 failed 當成零 findings。

## 4. 之後要跑完整 GPTScan

選擇解壓後 `archive_plan.json` 的一筆，使用它的 archive/build_json。
`legacy=true` 用 `--legacy-archive`，其餘用 `--archive`；有 target_roots 時逐項
加 `--target-root`。再加上 `--run-analysis` 與 gateway 設定，例如：

```bash
.venv/bin/python scripts/run_reusable.py \
  --reusable-root /path/to/prototype-reusable-dataset \
  --repo-id 2021-04-marginswap \
  --build-json outputs/bundle-inputs/2021-04-marginswap/build.json \
  --legacy-archive outputs/bundle-inputs/2021-04-marginswap/analysis_artifacts/2021-04-marginswap_export_archive.json \
  --run-analysis \
  --token-file /path/to/authorized/auth-gateway.token \
  --model openai-codex/gpt-5.6-luna \
  --timeout-minutes 30 \
  --output-dir outputs/marginswap-analysis
```

這一步才會使用模型額度並嘗試產生 `output.json`／`prediction_case.json`。
不要把 preflight 成功解讀為已經驗證完整模型分析成功。

## 分析範圍與授權

Production roots 與依賴閉包選擇保留在 manifest；不是偵測所有測試／script／vendor。
部分 Yul memory/storage builtins 採 opaque call 表示，並非完整 transient-storage alias model。
完整修正說明見 [COMPATIBILITY_20261105_ZH.md](../../docs/COMPATIBILITY_20261105_ZH.md)。

Source 與編譯產物屬於各 upstream 專案，適用各自授權；嵌入 source 的 SPDX／copyright
保留不變。沒有找到頂層 license 檔時，請以 manifest 的 upstream repo 查閱授權；
不宣稱本 fork 的 License 統一涵蓋所有第三方合約。

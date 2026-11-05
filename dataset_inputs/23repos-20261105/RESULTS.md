# Bundle 解壓後接入驗證

這是使用本資料夾壓縮檔解壓後重新驗證的結果：**23/23 ready_for_analysis**。
沒有呼叫模型，沒有進行 LLM Judge；不代表完整 GPTScan 或偵測效果已驗證。

| Repo | 接入 | Falcon contracts | Parser functions | 模式 |
|---|---|---:|---:|---|
| 2021-04-marginswap | 通過 | 28 | 110 | source-compared |
| 2021-07-spartan | 通過 | 25 | 139 | strict sidecar |
| 2021-08-notional | 通過 | 86 | 184 | source-compared |
| 2021-11-malt | 通過 | 80 | 248 | strict sidecar |
| 2021-12-vader | 通過 | 99 | 78 | strict sidecar |
| 2022-01-behodler | 通過 | 127 | 163 | strict sidecar |
| 2022-01-sandclock | 通過 | 32 | 26 | strict sidecar |
| 2022-08-sentiment | 通過 | 5 | 2 | strict sidecar |
| 2022-09-notional | 通過 | 111 | 115 | strict sidecar |
| 2022-11-paraspace | 通過 | 419 | 500 | strict sidecar |
| 2022-11-telcoin | 通過 | 37 | 16 | strict sidecar |
| 2023-03-olympus | 通過 | 47 | 55 | strict sidecar |
| 2023-04-blueberry | 通過 | 144 | 100 | source-compared |
| 2023-05-ussd | 通過 | 45 | 25 | source-compared |
| 2023-06-lybra | 通過 | 110 | 114 | strict sidecar |
| 2023-06-real-wagmi | 通過 | 39 | 27 | strict sidecar |
| 2023-06-tokemak | 通過 | 261 | 233 | strict sidecar |
| 2023-08-dopex | 通過 | 111 | 131 | source-compared |
| 2024-03-abracadabra-money | 通過 | 87 | 120 | source-compared |
| 2024-03-revert-lend | 通過 | 63 | 83 | strict sidecar |
| 2024-03-woofi-swap | 通過 | 114 | 273 | strict sidecar |
| 2024-04-panoptic | 通過 | 39 | 146 | strict sidecar |
| 2025-12-panoptic | 通過 | 83 | 223 | source-compared |

輸入 manifest SHA256 與 code snapshot commit 見 [ROUNDTRIP_VALIDATION.json](ROUNDTRIP_VALIDATION.json)。


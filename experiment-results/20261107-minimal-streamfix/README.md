# GPTScan 最小適配＋串流修正實驗（2026-11-07）

23 個 repo，92 筆候選 findings，42 筆 ground truth；正式 LLM Judge 已完成。

- [完整評估報告](evaluation/report.md)
- [實驗與原版差異](../../docs/GPTScan_20261107_完整實驗與原版差異.md)
- [重現指令](REPRODUCE.md)
- `predictions/`：23 份原樣輸出的 Judge input。
- `evaluation/`：完整 canonical manifest、Judge artifact、JSON 與 Markdown 報告。
- `detector_source_snapshot/`、`source_hashes.json`：實驗當時程式碼，不含環境或憑證。
- `repo_summary.json`、`validation/`：執行完整性與格式驗證；未上傳用量稽核、raw runtime 或重複 archives。
- Evaluator 沒有重寫；取得 prototype 的固定 commit 後可用 `evaluator_source_hashes.json` 查核。

| Repo | 狀態 | Findings | Schema |
|---|---|---:|---|
| 2021-04-marginswap | completed | 2 | 通過 |
| 2021-07-spartan | completed_with_errors | 5 | 通過 |
| 2021-08-notional | completed_with_errors | 3 | 通過 |
| 2021-11-malt | completed | 1 | 通過 |
| 2021-12-vader | completed_with_errors | 5 | 通過 |
| 2022-01-behodler | completed_with_errors | 10 | 通過 |
| 2022-01-sandclock | completed | 0 | 通過 |
| 2022-08-sentiment | completed | 0 | 通過 |
| 2022-09-notional | completed_with_errors | 4 | 通過 |
| 2022-11-paraspace | completed_with_errors | 0 | 通過 |
| 2022-11-telcoin | completed | 0 | 通過 |
| 2023-03-olympus | completed_with_errors | 1 | 通過 |
| 2023-04-blueberry | completed | 4 | 通過 |
| 2023-05-ussd | completed_with_errors | 0 | 通過 |
| 2023-06-lybra | completed | 3 | 通過 |
| 2023-06-real-wagmi | completed | 6 | 通過 |
| 2023-06-tokemak | completed_with_errors | 9 | 通過 |
| 2023-08-dopex | completed_with_errors | 1 | 通過 |
| 2024-03-abracadabra-money | completed_with_errors | 5 | 通過 |
| 2024-03-revert-lend | completed_with_errors | 13 | 通過 |
| 2024-03-woofi-swap | completed | 11 | 通過 |
| 2024-04-panoptic | completed_with_errors | 3 | 通過 |
| 2025-12-panoptic | completed_with_errors | 6 | 通過 |

9 個 completed、14 個 completed_with_errors；後者不表示全部候選成功。這輪未觀察到串流失敗／傳輸重試／問答timeout。
保留原始 findings，不手補 mitigation、不挑最好一次。Soft precision 0.0484、soft recall 0.1060、pooled soft F1 0.0664。
沒有包含原始 dataset git checkouts、build caches、Python environments、OAuth credentials 或 gateway token。

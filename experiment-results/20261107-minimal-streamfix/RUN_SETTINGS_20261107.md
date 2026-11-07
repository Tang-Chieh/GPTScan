# 2026-11-07 串流修正後完整重跑

本輪是新的23-repo GPTScan + LLM Judge實驗，不是11/06舊結果；入口自動產生的README標題日期沿用舊模板，實際開始時間以workflow_status.json為準。

- 使用最小適配baseline，保留原版候選級容錯、七條原版規則只補impact、原版system prompt附加price scope。
- 包含11/07的SSE framing、錯誤分類與有限次同請求傳輸重試。對照 GATEWAY_STREAM_FIX_20261107_ZH.md。
- Detector：openai-codex/gpt-5.6-luna；Judge：gpt-5.6-luna，end-to-end-v2，與前輪相同evaluator／ground truth。
- 每repo60分鐘、單次問答180秒；先做OAuth smoke，再跑全部repo，最後評估23份合法輸出。
- 所有repo重新分析，不挑最好結果、不混入舊PredictionCase。
- completed_with_errors仍可將實際合法輸出送Judge，但必須另外披露錯誤，不宣稱所有候選成功。
- 若有fatal failure、timeout或無效schema，不捏造空input，完整Judge先停止。
- 原始碼、source hashes、patch、archive plan及evaluator均由入口保存。
- 新結果不覆蓋舊實驗；沒有commit/push。

## 即時檔案

- gptscan/README.md：逐repo更新的總表，GPTScan batch啟動後才存在。
- workflow_status.json：整體階段、Judge是否開始及是否成功。
- judge_smoke.log、gptscan.log、llm_judge.log：各階段紀錄。
- llm_judge/report.md：正式評估成功後才會出現。

請避免電腦睡眠／關蓋造成程序長時間暫停；caffeinate -i只能防止一般idle sleep，不能保證所有情況。若再出現長空檔或wall time超過設定，須記錄而非宣稱嚴格符合時間預算。

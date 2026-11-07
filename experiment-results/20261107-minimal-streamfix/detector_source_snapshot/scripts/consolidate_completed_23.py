#!/usr/bin/env python3
"""Collect the successful original run and explicit successful retries, unchanged."""
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def main():
    outputs = ROOT / 'outputs'
    original = outputs / 'dataset-23-full-20261105'
    retry = outputs / 'dataset-3-retry-60min-20261105'
    paraspace = outputs / 'paraspace-retry-180s-20261105'
    summary = json.loads((original / 'summary.json').read_text())
    out = outputs / 'dataset-23-consolidated-20261105'
    out.mkdir(exist_ok=False)
    predictions = out / 'predictions'
    predictions.mkdir()
    cases = []
    metadata = None
    rows = ['# GPTScan 23 Repo 完整結果總表', '',
            '彙整各 repo 最新成功結果，保留原始 findings，不補寫語意欄位、不修改模型結果。', '',
            '本檔記錄 GPTScan 結果；LLM Judge 是否完成請另外查看 `llm_judge/report.md`。', '',
            '| Repo | GPTScan | Findings | Repo 時限（分鐘） | 單次問答時限（秒） | 格式驗證 | 來源 |',
            '|---|---|---:|---:|---:|---|---|']
    for repo_id in summary['repo_ids']:
        source = (paraspace if repo_id == '2022-11-paraspace' else
                  retry / repo_id if repo_id in ('2024-03-woofi-swap', '2025-12-panoptic') else
                  original / repo_id)
        manifest = json.loads((source / 'adapter_manifest.json').read_text())
        if manifest['status'] != 'completed':
            raise ValueError(f'{repo_id} did not complete')
        schema_log = source / 'schema_validation.log'
        if not schema_log.is_file() or 'PredictionCase validated:' not in schema_log.read_text():
            raise ValueError(f'{repo_id} has no passing schema validation')
        prediction_path = source / 'prediction_case.json'
        case = json.loads(prediction_path.read_text())
        if case['repo_id'] != repo_id:
            raise ValueError('Repository identity mismatch')
        if metadata is None:
            metadata = case['detector_metadata']
        if case['detector_metadata'] != metadata:
            raise ValueError('Detector metadata differs; do not silently overwrite it')
        shutil.copyfile(prediction_path, predictions / f'{repo_id}.json')
        count = len(case['predictions'])
        wall = manifest.get('model_question_timeout_seconds', 90)
        budget = manifest['analysis_timeout_minutes']
        entry = {'repo_id': repo_id, 'status': 'completed', 'schema_validated': True,
                 'prediction_count': count, 'source_directory': str(source),
                 'prediction_sha256': hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
                 'analysis_timeout_minutes': budget, 'model_question_timeout_seconds': wall,
                 'detector_commit': manifest.get('detector_commit'),
                 'detector_dirty': manifest.get('detector_dirty'),
                 'prediction_case': case}
        cases.append(entry)
        rows.append(f'| {repo_id} | 成功 | {count} | {budget:g} | {wall:g} | 通過 | [紀錄]({source / "adapter_manifest.json"}) |')
    if len(cases) != 23 or len({r['repo_id'] for r in cases}) != 23:
        raise ValueError('Expected exactly 23 unique repos')
    total = sum(r['prediction_count'] for r in cases)
    rows += ['', f'合計：23／23 成功；{total} 筆候選 findings；23 份 PredictionCase 通過格式驗證。', '',
             '## 解讀限制', '',
             '- Findings 是工具候選結果，不代表已確認漏洞；命中情形由後續 Judge 評估。',
             '- Sentiment 為零候選／未進入模型分析；Telcoin 有模型分析但零 findings。不能把零 findings 當成安全證明。',
             '- 原批次為每 repo 30 分鐘；Woofi、2025 Panoptic 補跑為 60 分鐘；ParaSpace 最終補跑為 60 分鐘且單次問答 180 秒。',
             '- Woofi、2025 Panoptic、ParaSpace 使用修正後的 JSON prompt。這是一份混合預算／修正版補跑完成集，不是所有 repo 同一設定重跑的控制實驗。',
             '- Detector metadata 維持原檔；詳細版本、補跑設定及內容雜湊保存在 `consolidated_results.json`。',
             '- 一份完整資料檔：`consolidated_results.json`；Judge 的目錄格式輸入：`predictions/<repo_id>.json`。',
             '- 後續評估輸出：`llm_judge/`，完成後會產生 `report.md`。', '']
    (out / 'README.md').write_text('\n'.join(rows))
    (out / 'consolidated_results.json').write_text(json.dumps({
        'created_at': datetime.now(timezone.utc).isoformat(), 'repo_count': len(cases),
        'prediction_count': total, 'mixed_run_settings': True,
        'cases': cases}, ensure_ascii=False, indent=2) + '\n')
    print(f'{out}: {len(cases)} repos, {total} predictions')


if __name__ == '__main__':
    main()

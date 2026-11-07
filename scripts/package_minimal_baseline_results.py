#!/usr/bin/env python3
"""Publish an allowlisted experiment receipt, not credentials or build workspaces."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.destination.resolve()
    if not json.loads((source / 'workflow_status.json').read_text()).get('judge_completed'):
        parser.error('Only completed Judge runs may be packaged')
    out.mkdir(parents=True, exist_ok=False)

    def copy(relative, target=None):
        dest = out / (target or relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, dest)

    for name in ('workflow_status.json', 'source_hashes.json', 'detector_changes.patch',
                 'RUN_SETTINGS_20261107.md', 'gptscan.log', 'llm_judge.log'):
        copy(name)
    for name in ('manifest.json', 'judge_artifact.json', 'report.json', 'report.md'):
        copy('llm_judge/' + name, 'evaluation/' + name)
    shutil.copytree(source / 'gptscan/predictions', out / 'predictions')
    shutil.copytree(source / 'detector_source_snapshot', out / 'detector_source_snapshot',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    summary = json.loads((source / 'gptscan/summary.json').read_text())
    repos = []
    for repo_id, record in summary['repos'].items():
        repos.append({key: record.get(key) for key in ('repo_id', 'status', 'stage', 'prediction_count',
            'schema_validated', 'processing_completed', 'analysis_complete', 'analysis_error_events',
            'analysis_timeout_minutes', 'model_question_timeout_seconds', 'elapsed_seconds', 'failure')})
        copy(f'gptscan/{repo_id}/schema_validation.log', f'validation/{repo_id}.log')
    (out / 'repo_summary.json').write_text(json.dumps(repos, ensure_ascii=False, indent=2) + '\n')
    evaluator_hashes = {str(p.relative_to(source / 'evaluator_source')):
                        hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (source / 'evaluator_source').rglob('*')
                        if p.is_file() and p.suffix in ('.py', '.json', '.md')}
    (out / 'evaluator_source_hashes.json').write_text(json.dumps(evaluator_hashes, indent=2) + '\n')
    rows = ['# GPTScan 最小適配＋串流修正實驗（2026-11-07）', '',
            '23 個 repo，92 筆候選 findings，42 筆 ground truth；正式 LLM Judge 已完成。', '',
            '- [完整評估報告](evaluation/report.md)',
            '- [實驗與原版差異](../../docs/GPTScan_20261107_完整實驗與原版差異.md)',
            '- [重現指令](REPRODUCE.md)',
            '- `predictions/`：23 份原樣輸出的 Judge input。',
            '- `evaluation/`：完整 canonical manifest、Judge artifact、JSON 與 Markdown 報告。',
            '- `detector_source_snapshot/`、`source_hashes.json`：實驗當時程式碼，不含環境或憑證。',
            '- `repo_summary.json`、`validation/`：執行完整性與格式驗證；未上傳用量稽核、raw runtime 或重複 archives。',
            '- Evaluator 沒有重寫；取得 prototype 的固定 commit 後可用 `evaluator_source_hashes.json` 查核。', '',
            '| Repo | 狀態 | Findings | Schema |', '|---|---|---:|---|']
    for row in repos:
        rows.append(f"| {row['repo_id']} | {row['status']} | {row['prediction_count']} | {'通過' if row['schema_validated'] else '未通過'} |")
    rows += ['', '9 個 completed、14 個 completed_with_errors；後者不表示全部候選成功。這輪未觀察到串流失敗／傳輸重試／問答timeout。',
             '保留原始 findings，不手補 mitigation、不挑最好一次。Soft precision 0.0484、soft recall 0.1060、pooled soft F1 0.0664。',
             '沒有包含原始 dataset git checkouts、build caches、Python environments、OAuth credentials 或 gateway token。', '']
    (out / 'README.md').write_text('\n'.join(rows))
    # Check only concrete credential encodings; do not print candidate secret values.
    patterns = [r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}', r'\bgh[pousr]_[A-Za-z0-9]{20,}',
                r'\bgithub_pat_[A-Za-z0-9_]{20,}', r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}',
                r'\bac_[A-Za-z0-9_-]{25,}']
    suspicious = [str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()
                  and any(re.search(pattern, p.read_text(errors='replace')) for pattern in patterns)]
    if suspicious:
        raise ValueError('Potential credential encodings found; do not commit: ' + repr(suspicious))
    print(f'Packaged {len(repos)} repos and canonical evaluation artifacts into {out}')


if __name__ == '__main__':
    main()

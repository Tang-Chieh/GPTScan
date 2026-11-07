#!/usr/bin/env python3
"""Frozen-input 23-repo run followed by the unchanged canonical OAuth Judge."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--run-judge', action='store_true', help='Explicit opt-in; by default run GPTScan only')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    evaluator = out / 'evaluator_source'
    prior = ROOT / 'outputs/dataset-23-consolidated-20261105/evaluator_source'
    shutil.copytree(prior, evaluator, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    plan = ROOT / 'outputs/bundle-23-20261105/unpacked/archive_plan.json'
    shutil.copyfile(plan, out / 'archive_plan.json')
    source_snapshot = out / 'detector_source_snapshot'
    for directory in ('src', 'scripts'):
        for path in (ROOT / directory).rglob('*'):
            if not path.is_file() or path.suffix not in ('.py', '.yml', '.yaml', '.json') or '__pycache__' in path.parts:
                continue
            target = source_snapshot / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    (out / 'detector_changes.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT))
    files = {str(p.relative_to(source_snapshot)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in source_snapshot.rglob('*') if p.is_file()}
    (out / 'source_hashes.json').write_text(json.dumps(files, indent=2) + '\n')
    state = {'status': 'running', 'stage': 'judge_smoke',
             'started_at': datetime.now(timezone.utc).isoformat(),
             'detector_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'detector_uncommitted_changes_snapshotted': True,
             'evaluator_commit': 'e46fc2702a1c6506f9a56af00990f8218648f697',
             'detector_model': 'openai-codex/gpt-5.6-luna', 'judge_model': 'gpt-5.6-luna',
             'analysis_timeout_minutes': 60, 'model_question_timeout_seconds': 180,
             'price_system_prompt_retained': True, 'rule_profile': 'upstream7-minimal-baseline-v3',
             'analysis_policy': 'upstream candidate-level exceptions; no global ERROR veto',
             'judge_started': False, 'judge_completed': False}

    def save():
        temp = out / 'workflow_status.json.tmp'
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
        temp.replace(out / 'workflow_status.json')

    def run(command, cwd, log):
        with (out / log).open('w') as stream:
            return subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode

    save()
    (out / 'README.md').write_text('''# GPTScan 最小適配 baseline 實驗（2026-11-06）

23 repo 固定 archive；七條 upstream rules 只補 impact，原 recommendation 不變；原版 system prompt 只附加 price-focused 指令。
模型 gpt-5.6-luna，每 repo 60 分鐘、單次模型問答及 transport timeout 180 秒。
主要輸出直接為 PredictionCase，沒有外部轉檔或人工補寫 mitigation。

## 查看進度

- [workflow_status.json](workflow_status.json)：整體執行階段與成功／阻擋狀態。
- [judge_smoke.log](judge_smoke.log)：既有 OAuth 驗證及 smoke。
- [GPTScan 逐 repo 總表](gptscan/README.md)：批次 runner 自動更新；該頁僅記錄 GPTScan，Judge 狀態見整體 workflow。
- [gptscan.log](gptscan.log)：批次啟動／完成記錄；詳細分析見各 repo 的 execution.log。
- [llm_judge.log](llm_judge.log)：完整 Judge 進度，開始後才存在。
- [最終 Judge 報告](llm_judge/report.md)：完整成功後才存在。

## 執行原則

明確帶 --run-judge 時先跑 OAuth smoke，再完整 GPTScan；23 份 PredictionCase 均可產出並驗證後才執行 Judge。
completed_with_errors 表示沿原版例外處理跑到結束且有合法輸出，但不代表所有候選分析成功；錯誤另列，不刪除或改寫 findings。
若有失敗／逾時／schema error，保留記錄、停止在評估前，不默默刪除失敗 repo 或用舊結果替代。
來源保存在 detector_source_snapshot/、source_hashes.json 與 detector_changes.patch；評估器與 ground truth 快照在 evaluator_source/。
沿用上一輪評估版本與相同 ground truth，無另外修改 Judge prompt 或分數。
原始 dataset、舊實驗結果與 GitHub 都不改動；不 commit/push，不複製 OAuth 憑證。
''')
    judge_python = str(ROOT.parent / 'prototype-scar/.venv/bin/python')
    judge_base = [judge_python, '-u', '-m', 'src.benchmark_eval', '--auth-mode', 'oauth',
                  '--judge-model', 'gpt-5.6-luna']
    try:
        code = run(judge_base + ['--ground-truth-dir', 'examples/benchmark_eval/price-manipulation-smoke/ground_truth',
                   '--predictions-dir', 'examples/benchmark_eval/price-manipulation-smoke/predictions',
                   '--output-dir', str(out / 'judge_smoke')], evaluator, 'judge_smoke.log') if args.run_judge else 0
        if code:
            state.update(status='blocked', failure='OAuth smoke failed; inspect judge_smoke.log', exit_code=code)
            save()
            return 1
        state['stage'] = 'gptscan'
        save()
        code = run([sys.executable, '-u', str(ROOT / 'scripts/run_reusable_batch.py'),
                    '--plan', str(out / 'archive_plan.json'),
                    '--reusable-root', str(ROOT.parent / 'prototype-reusable-dataset'),
                    '--contract-file', str(evaluator / 'src/benchmark_eval/contract.py'),
                    '--token-file', str(ROOT.parent / 'subscription-gateway-pilot/runtime-home/.omp/auth-gateway.token'),
                    '--model', 'openai-codex/gpt-5.6-luna', '--timeout-minutes', '60',
                    '--request-timeout-seconds', '180', '--output-dir', str(out / 'gptscan')], ROOT, 'gptscan.log')
        summary = json.loads((out / 'gptscan/summary.json').read_text())
        repos = summary.get('repos', {})
        failed = {r: v.get('status') for r, v in repos.items()
                  if v.get('status') not in ('completed', 'completed_with_errors') or not v.get('schema_validated')}
        state['repos_with_analysis_errors'] = [r for r,v in repos.items() if v.get('status') == 'completed_with_errors']
        if code or summary.get('status') != 'finished' or len(repos) != 23 or failed:
            state.update(status='blocked', stage='gptscan', failed_repos=failed,
                         failure='Not all 23 repos completed and passed schema; Judge not started')
            save()
            return 1
        if not args.run_judge or (out / 'SKIP_LLM_JUDGE.md').exists():
            state.update(status='completed', stage='gptscan_complete', judge_started=False,
                         judge_completed=False, judge_skipped=True,
                         finished_at=datetime.now(timezone.utc).isoformat())
            save()
            return 0
        # Detect working-tree code edits during the long run, without altering artifacts.
        changed = [name for name, digest in files.items()
                   if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
        if changed:
            state.update(status='blocked', failure='Detector source changed during experiment', changed_source_files=changed)
            save()
            return 1
        state.update(stage='llm_judge', judge_started=True)
        save()
        code = run(judge_base + ['--ground-truth-dir', 'dataset/downstream-stage1/pilot-v1/ground_truth',
                   '--predictions-dir', str(out / 'gptscan/predictions'),
                   '--output-dir', str(out / 'llm_judge')], evaluator, 'llm_judge.log')
        complete = code == 0 and (out / 'llm_judge/report.md').is_file()
        state.update(status='completed' if complete else 'failed', stage='complete' if complete else 'llm_judge',
                     judge_completed=complete, exit_code=code, finished_at=datetime.now(timezone.utc).isoformat())
        save()
        return 0 if complete else 1
    except Exception as error:
        state.update(status='failed', failure=f'{type(error).__name__}: {error}')
        save()
        raise


if __name__ == '__main__':
    raise SystemExit(main())

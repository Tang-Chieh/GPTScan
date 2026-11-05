#!/usr/bin/env python3
"""Sequential reusable builds and GPTScan; validate predictions, never invoke Judge."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    selection_group = p.add_mutually_exclusive_group(required=True)
    selection_group.add_argument('--selection', type=Path, help='Legacy build-based selection')
    selection_group.add_argument('--plan', type=Path, help='Verified unpacked archive plan (recommended)')
    p.add_argument('--reusable-root', type=Path, required=True)
    p.add_argument('--contract-file', type=Path, required=True)
    p.add_argument('--token-file', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--timeout-minutes', type=float, default=30)
    p.add_argument('--model', default='openai-codex/gpt-5.6-luna')
    p.add_argument('--gateway-url', default='http://127.0.0.1:4000/v1')
    p.add_argument('--gateway-database', type=Path, help='Optional usage-only SQLite snapshots; credentials are never read')
    p.add_argument('--audit-dir', type=Path, help='Optional pre-run audit evidence (only three named usage files are copied)')
    args = p.parse_args()
    plan = json.loads(args.plan.read_text()) if args.plan else json.loads(args.selection.read_text())['repos']
    ids = [r['repo_id'] for r in plan]
    if len(ids) != len(set(ids)):
        p.error('Duplicate repository IDs')
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'predictions').mkdir()
    if args.audit_dir:
        evidence = out / 'audit_before'
        evidence.mkdir()
        for name in ('app_quota_before.json', 'gateway_before.json', 'smoke_events.jsonl'):
            source = args.audit_dir / name
            if source.is_file():
                shutil.copyfile(source, evidence / name)
    def usage_snapshot(name):
        if args.gateway_database:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/record_gateway_usage.py'),
                                     '--database', str(args.gateway_database.resolve()), '--output', str(out / name)],
                                    capture_output=True, text=True)
            if result.returncode:
                save(out / (name + '.error.json'), {'error': 'Usage snapshot unavailable; not a model failure'})
    usage_snapshot('gateway_before.json')
    # Copy only the validation schema, not ground-truth findings.
    contract = out / 'contract_snapshot.py'
    shutil.copyfile(args.contract_file, contract)
    save(out / 'input_plan.json', plan)
    summary = {'model': args.model, 'judge_executed': False, 'provider': 'codex-gateway',
               'started_at': datetime.now(timezone.utc).isoformat(),
               'detector_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'contract_sha256': hashlib.sha256(contract.read_bytes()).hexdigest(),
               'analysis_timeout_minutes': args.timeout_minutes, 'repo_ids': ids,
               'status': 'running', 'repos': {}}

    def publish():
        summary['completed_model_requests'] = sum(r.get('completed_model_requests', 0) for r in summary['repos'].values())
        summary['usage'] = {key: sum(r.get('usage', {}).get(key, 0) for r in summary['repos'].values())
                           for key in ('input_tokens', 'output_tokens', 'cached_tokens', 'reasoning_tokens')
                           if any(key in r.get('usage', {}) for r in summary['repos'].values())}
        save(out / 'summary.json', summary)
        rows = ['# GPTScan → Judge input 批次結果', '',
                '僅執行 GPTScan 與 PredictionCase schema 驗證；未執行 LLM Judge。', '',
                f"批次狀態：{summary['status']}；已完成模型請求：{summary['completed_model_requests']}；已回報 usage：{summary['usage']}", '',
                '| Repo | 狀態 | 階段 | Model calls | Findings | 原因 |', '|---|---|---|---:|---:|---|']
        for name in ids:
            r = summary['repos'].get(name, {})
            reason = str(r.get('failure', '')).replace('|', '/').replace('\n', ' ')
            rows.append(f"| {name} | {r.get('status', 'pending')} | {r.get('stage', '')} | {r.get('completed_model_requests', '')} | {r.get('prediction_count', '')} | {reason} |")
        (out / 'README.md').write_text('\n'.join(rows) + '\n')

    publish()
    def audit(run, record):
        event_file = run / 'model_events.jsonl'
        events = []
        if event_file.exists():
            for line in event_file.read_text().splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # next progress refresh will read a completed last line
        record['completed_model_requests'] = sum(e.get('status') == 'completed' for e in events)
        record['failed_model_requests'] = sum(e.get('status') == 'failed' for e in events)
        metadata = [e for e in events if e.get('status') == 'response_metadata']
        record['server_models'] = sorted({e['server_model'] for e in metadata if e.get('server_model')})
        record['usage'] = {key: sum(e['usage'][key] for e in metadata if key in e.get('usage', {}))
                           for key in ('input_tokens', 'output_tokens', 'cached_tokens', 'reasoning_tokens')
                           if any(key in e.get('usage', {}) for e in metadata)}
        return any(e.get('http_status') in (401, 403, 429) for e in events)

    for number, item in enumerate(plan, 1):
        name = item['repo_id']
        started = time.time()
        record = {'status': 'running', 'stage': 'adapter'}
        summary['repos'][name] = record
        publish()
        print(f'[{number}/{len(ids)}] START {name}', flush=True)
        run = out / name
        command = [sys.executable, str(ROOT / 'scripts/run_reusable.py'),
                   '--reusable-root', str(args.reusable_root.resolve()), '--repo-id', name,
                   '--run-analysis', '--token-file', str(args.token_file.resolve()),
                   '--model', args.model, '--gateway-url', args.gateway_url,
                   '--timeout-minutes', str(args.timeout_minutes), '--output-dir', str(run)]
        if args.plan:
            command += ['--legacy-archive' if item.get('legacy') else '--archive', item['archive']]
            if item.get('build_json'):
                command += ['--build-json', item['build_json']]
            for target in item.get('target_roots', []):
                command += ['--target-root', target]
        try:
            with (out / f'{name}.log').open('w') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                while True:
                    try:
                        code = process.wait(timeout=5)
                        break
                    except subprocess.TimeoutExpired:
                        manifest = run / 'adapter_manifest.json'
                        if manifest.exists():
                            try:
                                record['stage'] = json.loads(manifest.read_text()).get('stage', 'adapter')
                            except json.JSONDecodeError:
                                pass
                        audit(run, record)
                        record['elapsed_seconds'] = round(time.time() - started, 2)
                        publish()
            manifest = run / 'adapter_manifest.json'
            if manifest.exists():
                record.update(json.loads(manifest.read_text()))
            else:
                record.update(status='failed', failure='Adapter stopped before manifest; inspect batch log')
            record['exit_code'] = code
            if code == 0 and record.get('status') == 'completed':
                check = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_prediction.py'),
                                        '--contract-file', str(contract), '--prediction', str(run / 'prediction_case.json')],
                                       cwd=ROOT, capture_output=True, text=True)
                (run / 'schema_validation.log').write_text(check.stdout + check.stderr)
                if check.returncode:
                    record.update(status='schema_failed', stage='schema', failure='PredictionCase schema validation failed')
                else:
                    record['schema_validated'] = True
                    shutil.copyfile(run / 'prediction_case.json', out / 'predictions' / f'{name}.json')
                    if not record.get('completed_model_requests'):
                        record['coverage_note'] = 'No model calls; candidate filtering did not enter LLM analysis'
        except Exception as error:
            record.update(status='failed', failure=f'{type(error).__name__}: {error}')
        record['elapsed_seconds'] = round(time.time() - started, 2)
        auth_or_quota = audit(run, record)
        publish()
        print(f"[{number}/{len(ids)}] {record['status']} {name}", flush=True)
        if auth_or_quota:
            summary.update(status='blocked_auth_or_quota', stopped_at=datetime.now(timezone.utc).isoformat())
            publish()
            usage_snapshot('gateway_after.json')
            print('Stopped: OAuth/model access/quota needs attention; no API/model fallback', flush=True)
            return
    summary['status'] = 'finished'
    summary['finished_at'] = datetime.now(timezone.utc).isoformat()
    usage_snapshot('gateway_after.json')
    publish()


if __name__ == '__main__':
    main()

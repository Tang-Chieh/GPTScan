"""Summarize preflight receipts, not detection accuracy or Judge results."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--checks', type=Path, required=True)
p.add_argument('--previous', type=Path, required=True)
p.add_argument('--output-dir', type=Path, required=True)
args = p.parse_args()
checks = json.loads((args.checks / 'summary.json').read_text())
previous = json.loads(args.previous.read_text())
if checks['status'] != 'finished' or set(checks['repos']) != set(previous['repo_ids']):
    raise ValueError('Incomplete dataset check; cannot summarize as a complete batch')
report = {'judge_executed': False, 'new_real_predictions': 0, 'repos': {}}
rows = ['# GPTScan Dataset 接入驗證（2026-11-05）', '',
        '這是無模型 preflight，不是完整 GPTScan 分析或 LLM Judge。舊 11/4 結果保留。', '',
        '| Repo | 11/4 狀態 | 本次接入 | Falcon contracts | Parser functions | Archive 模式 |',
        '|---|---|---|---:|---:|---|']
for name in previous['repo_ids']:
    record = checks['repos'][name]
    folder = args.checks / name
    manifest = json.loads((folder / 'adapter_manifest.json').read_text())
    preflight = manifest.get('archive_check', {})
    report['repos'][name] = {'status': record['status'], 'previous_status': previous['repos'][name]['status'],
                            'archive_check': preflight, 'legacy': record['legacy'],
                            'manifest': str((folder / 'adapter_manifest.json').resolve())}
    rows.append(f"| {name} | {previous['repos'][name]['status']} | {record['status']} | {preflight.get('falcon_contracts', '')} | {preflight.get('parser_functions', '')} | {'source-compared（無 sidecar attestation）' if record['legacy'] else 'strict sidecar'} |")
passed = sum(r['status'] == 'ready_for_analysis' for r in checks['repos'].values())
report['passed'] = passed
report['total'] = len(checks['repos'])
rows += ['', f'接入通過：{passed}/{report["total"]}。不能據此聲稱漏洞召回率或完整模型分析成功。', '',
         '分析限制：production roots／dependency 排除範圍已記在各 scope；Yul memory/storage builtins 為 opaque calls，未建立完整 transient-storage alias model。',
         '完整 GPTScan 仍需另外執行；新的 predictions 與 Judge report 本次沒有產生。']
root = Path(__file__).resolve().parents[1]
report['source_sha256'] = {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
                         for base in ('src', 'scripts') for f in (root / base).rglob('*.py')}
args.output_dir.mkdir(parents=True, exist_ok=True)
(args.output_dir / '接入驗證總表.md').write_text('\n'.join(rows) + '\n')
(args.output_dir / '接入驗證總表.json').write_text(json.dumps(report, indent=2))
print(f'Preflight passed: {passed}/{report["total"]}; no model/Judge evaluation')

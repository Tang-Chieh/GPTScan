"""Execute an explicit per-repo archive plan, preflight only (no model/Judge)."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--reusable-root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    plan = json.loads(args.plan.read_text())
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    summary = {'model_requests': 0, 'judge_executed': False, 'status': 'running', 'repos': {}}
    for item in plan:
        name = item['repo_id']
        run = out / name
        command = [sys.executable, str(ROOT / 'scripts/run_reusable.py'),
                   '--reusable-root', str(args.reusable_root.resolve()), '--repo-id', name,
                   '--legacy-archive' if item.get('legacy') else '--archive', item['archive'],
                   '--output-dir', str(run)]
        for root in item.get('target_roots', []):
            command += ['--target-root', root]
        if item.get('build_json'):
            command += ['--build-json', item['build_json']]
        with (out / (name + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        manifest = run / 'adapter_manifest.json'
        record = json.loads(manifest.read_text()) if manifest.exists() else {'status': 'failed'}
        summary['repos'][name] = {'status': record['status'], 'exit_code': result.returncode,
                                'failure': record.get('failure'), 'legacy': bool(item.get('legacy'))}
        (out / 'summary.json').write_text(json.dumps(summary, indent=2))
        print(name, record['status'], flush=True)
    summary['status'] = 'finished'
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()

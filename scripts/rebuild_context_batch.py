"""Rebuild scope-blocked projects with baseline framework inputs, no LLM calls."""
import json
from pathlib import Path
import subprocess
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
REUSABLE = ROOT.parent / 'prototype-reusable-dataset'
OUT = ROOT / 'outputs/compatibility-20261105'
IMAGE = 'sha256:9f007da176c2a3ae7e345510b1850968245f9a9cc8a33d64aec92a2aa24bc644'
p = argparse.ArgumentParser()
p.add_argument('--repos', nargs='+', default=['2023-05-ussd', '2023-08-dopex', '2024-03-abracadabra-money', '2025-12-panoptic'])
p.add_argument('--tag', default='context')
args = p.parse_args()
summary = {}
for name in args.repos:
    folder = OUT / (args.tag + '-' + name)
    folder.mkdir(exist_ok=False)
    command = ['docker', 'run', '--rm', '--name', 'gptscan-context-' + name, '--platform', 'linux/amd64',
               '-v', f'{REUSABLE}:/reusable:ro', '-v', f'{REUSABLE / "candidate-repos" / name}:/original:ro',
               '-v', f'{REUSABLE / "dataset/repos" / name}:/recipe:ro', '-v', f'{folder}:/result',
               '-v', f'{ROOT / "scripts/build_compiler_context.py"}:/context.py:ro',
               '-v', f'{ROOT / "scripts/brownie_capture.py"}:/brownie_capture.py:ro',
               '-v', f'{ROOT / "scripts/export_brownie_capture.py"}:/export_brownie_capture.py:ro',
               '-v', 'pmdetector-reusable-cache:/cache', '--entrypoint', 'python', IMAGE, '/context.py']
    with (folder / 'container.log').open('w') as log:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            summary[name] = {'build_exit': result.returncode}
        except subprocess.TimeoutExpired:
            subprocess.run(['docker', 'rm', '-f', 'gptscan-context-' + name], capture_output=True)
            summary[name] = {'status': 'timed_out'}
    archives = list((folder / 'export').glob('*archive.json'))
    if len(archives) == 1:
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/import_legacy_archive.py'),
                                 '--archive', str(archives[0]), '--build-json', str(REUSABLE / 'dataset/repos' / name / 'build.json'),
                                 '--repo', str(REUSABLE / 'candidate-repos' / name), '--output-dir', str(folder / 'analysis')], cwd=ROOT)
        summary[name]['preflight_exit'] = result.returncode
    (OUT / (args.tag + '_summary.json')).write_text(json.dumps(summary, indent=2))
    print(name, summary[name], flush=True)

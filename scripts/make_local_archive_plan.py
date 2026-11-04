"""Assemble this workspace's recorded archives; never select from ground truth."""
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reusable = ROOT.parent / 'prototype-reusable-dataset'
results = ROOT / 'outputs/compatibility-20261105'
original = json.loads((ROOT / 'outputs/dataset-23-20261104/summary.json').read_text())
p = argparse.ArgumentParser()
p.add_argument('--allow-missing', action='store_true')
args = p.parse_args()
special = {
    '2021-04-marginswap': (reusable / 'dataset/repos/2021-04-marginswap/analysis_artifacts/2021-04-marginswap_export_archive.json', []),
    '2023-04-blueberry': (reusable / 'dataset/repos/2023-04-blueberry/analysis_artifacts/2023-04-blueberry_export_archive.json', []),
    '2023-05-ussd': (results / 'node-safe-v3-2023-05-ussd/export/contracts_export_archive.json', ['contracts']),
    '2023-08-dopex': (results / 'context-2023-08-dopex/export/contracts_export_archive.json', []),
    '2024-03-abracadabra-money': (results / 'context-2024-03-abracadabra-money/export/contracts_export_archive.json', ['src']),
    '2025-12-panoptic': (results / 'context-v2-2025-12-panoptic/export/contracts_export_archive.json', ['contracts']),
    '2021-08-notional': (results / 'brownie-v7-2021-08-notional/export-v2/brownie_complete_export_archive.json', ['contracts']),
}
plan = []
for name in original['repo_ids']:
    archive, roots = special.get(name, (ROOT / '.local/reusable-builds' / name / 'analysis_artifacts' / (name + '_export_archive.json'), []))
    if not archive.is_file():
        if args.allow_missing:
            print('Pending archive:', name)
            continue
        raise FileNotFoundError(archive)
    plan.append({'repo_id': name, 'archive': str(archive), 'legacy': name in special, 'target_roots': roots})
(results / 'archive_plan.json').write_text(json.dumps(plan, indent=2))
print('Wrote explicit archive plan:', len(plan))

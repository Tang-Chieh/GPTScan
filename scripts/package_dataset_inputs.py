"""Package validated archive inputs without local logs, credentials or snapshots."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scan(data):
    patterns = (rb'sk-[A-Za-z0-9_-]{24,}', rb'gh[pousr]_[A-Za-z0-9]{30,}',
                rb'github_pat_[A-Za-z0-9_]{30,}', rb'/Users/williamtang')
    if any(re.search(pattern, data) for pattern in patterns):
        raise ValueError('Potential credential or private host path found; package not published')


def save(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    scan(text.encode())
    path.write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--checks', type=Path, required=True)
    p.add_argument('--reusable-root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    plan = json.loads(args.plan.read_text())
    checks = json.loads((args.checks / 'summary.json').read_text())
    if checks['status'] != 'finished' or set(checks['repos']) != {x['repo_id'] for x in plan}:
        raise ValueError('Plan and completed check inventory differ')
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=False)
    index = {'schema_version': '1.0.0', 'validation': 'archive/Falcon/parser/CallGraph preflight only',
             'llm_judge_executed': False, 'new_model_predictions': False, 'repos': []}
    for item in plan:
        name = item['repo_id']
        if checks['repos'][name]['status'] != 'ready_for_analysis':
            raise ValueError(f'Input has not passed preflight: {name}')
        folder = out / name
        folder.mkdir()
        archive = Path(item['archive'])
        raw = archive.read_bytes()
        scan(raw)
        compressed = gzip.compress(raw, compresslevel=6, mtime=0)
        (folder / 'archive.json.gz').write_bytes(compressed)
        build_file = args.reusable_root / 'dataset/repos' / name / 'build.json'
        build_raw = build_file.read_bytes()
        scan(build_raw)
        (folder / 'build.json').write_bytes(build_raw)
        build = json.loads(build_raw)
        native = json.loads((args.checks / name / 'adapter_manifest.json').read_text())
        record = {'repo_id': name, 'repository_url': build['source']['repository_url'],
                  'source_commit': build['source']['ref'], 'archive': name + '/archive.json.gz',
                  'build_json': name + '/build.json', 'archive_sha256': digest(raw),
                  'gzip_sha256': digest(compressed), 'archive_bytes': len(raw), 'gzip_bytes': len(compressed),
                  'build_json_sha256': digest(build_raw), 'legacy': item.get('legacy', False),
                  'target_roots': item.get('target_roots', [])}
        receipt = {'repo_id': name, 'status': native['status'], 'check': native['archive_check'],
                   'source_commit': build['source']['ref'], 'archive_sha256': digest(raw),
                   'build_provenance_verified': not record['legacy'],
                   'note': 'Preflight only; no findings or Judge evaluation. Legacy imports have source comparison, not sidecar attestation.'}
        save(folder / 'preflight.json', receipt)
        if not record['legacy']:
            sidecar = archive.with_name(archive.stem + '.manifest.json')
            content = sidecar.read_bytes()
            scan(content)
            (folder / 'archive.manifest.json').write_bytes(content)
            record['sidecar_sha256'] = digest(content)
            result_file = archive.parent.parent / 'build_result.json'
            if result_file.is_file():
                result = json.loads(result_file.read_text())
                save(folder / 'toolchain.json', {'toolchain': result.get('toolchain', {}),
                                                'note': 'Toolchain-only copy of original build result; not a new build result.'})
                record['toolchain_sha256'] = digest((folder / 'toolchain.json').read_bytes())
        # Preserve upstream license notices separately; embedded SPDX headers
        # remain unchanged inside the byte-for-byte compiler archive.
        repo = args.reusable_root / build['source']['repo_path']
        working = repo / build['source'].get('working_directory', '.')
        licenses = sorted({f for base in (repo, working) for f in base.iterdir()
                           if f.is_file() and f.name.casefold().startswith(('license', 'copying', 'notice'))})
        for number, license_file in enumerate(licenses):
            path = folder / f'UPSTREAM_{number}_{license_file.name}'
            content = license_file.read_bytes()
            scan(content)
            path.write_bytes(content)
        index['repos'].append(record)
    save(out / 'manifest.json', index)
    print(f'Packaged {len(index["repos"])} archives; {sum(x["gzip_bytes"] for x in index["repos"])/1024/1024:.1f} MiB compressed')


if __name__ == '__main__':
    main()

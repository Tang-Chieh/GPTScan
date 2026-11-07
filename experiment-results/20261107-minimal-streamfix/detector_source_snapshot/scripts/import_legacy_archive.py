"""Explicit legacy archive import; verify embedded source, disclose missing provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from reusable_archive import materialize_archive, sha256
from archive_scope import production_archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--build-json', type=Path, required=True)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--target-root', action='append', default=[], help='Explicit compiler project-relative production directory; imports retained')
    args = p.parse_args()
    build = json.loads(args.build_json.read_text())
    repo = args.repo.resolve()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if commit != build['source']['ref']:
        raise ValueError('Repository commit differs from build recipe')
    data = json.loads(args.archive.read_text())
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if args.target_root:
        data, selection = production_archive(data, args.target_root)
        (out / 'compiler_scope_selection.json').write_text(json.dumps(selection, indent=2))
    manifest = {'archive_source_root': data['working_dir'],
                'analysis_scope': {'policy_version': 'legacy-embedded-sources',
                                   'provenance': 'source-compared; original build recipe not attested'}}
    rebased, scope = materialize_archive(data, manifest, build, out / 'source')
    compared, generated, mismatches, recipe_materialized = [], [], [], []
    working = Path(build['source'].get('working_directory', '.'))
    declared = {str(working / f['path']): hashlib.sha256(f['content'].encode()).hexdigest()
                for f in build.get('materialize', {}).get('files', [])}
    for name, expected in scope['source_files_sha256'].items():
        relative = Path(scope['original_relative_paths'][name])
        path = repo / relative
        if declared.get(str(relative)) == expected:
            recipe_materialized.append(str(relative))
        elif not path.is_file():
            generated.append(str(relative))
        elif sha256(path) != expected:
            mismatches.append(str(relative))
        else:
            compared.append(str(relative))
    report = {'repo_id': build['repo_id'], 'source_commit': commit,
              'original_archive_sha256': sha256(args.archive), 'source_compared': compared,
              'archive_only_sources': generated, 'mismatched_sources': mismatches,
              'recipe_materialized_sources': recipe_materialized,
              'build_provenance_verified': False,
              'warning': 'Legacy archive: original compiler invocation/recipe not attested. Archive-only generated dependencies remain explicitly listed.'}
    (out / 'legacy_import.json').write_text(json.dumps(report, indent=2))
    if mismatches or not compared:
        raise ValueError('Legacy archive source mismatch or no repository sources matched; see legacy_import.json')
    normalized = out / 'input_export_archive.json'
    normalized.write_text(json.dumps(rebased))
    scope['archive_sha256'] = sha256(normalized)
    (out / 'scope.json').write_text(json.dumps(scope))
    work = out / 'work'
    work.mkdir()
    for name in ('rules', 'jars', 'whitelist.json', 'modifier_whitelist.json'):
        (work / name).symlink_to(ROOT / 'src' / name)
    with (out / 'archive_check.log').open('w') as log:
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_archive.py'),
                                 '--archive', str(normalized), '--scope', str(out / 'scope.json'),
                                 '--output', str(out / 'archive_check.json')], cwd=work,
                                env={**os.environ, 'VIRTUAL_ENV': sys.prefix}, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('Legacy Falcon/parser preflight failed; see archive_check.log')
    print('READY legacy archive; provenance limitation recorded:', build['repo_id'])


if __name__ == '__main__':
    main()

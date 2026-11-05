"""Verify bundled inputs and produce a local archive plan; never invoke a model."""
import argparse
import gzip
import io
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    bundle = args.bundle.resolve()
    index = json.loads((bundle / 'manifest.json').read_text())
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    plan = []
    names = set()
    for item in index['repos']:
        name = item['repo_id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name) or name in names:
            raise ValueError('Unsafe or duplicate repo ID')
        names.add(name)
        def read(relative):
            path = (bundle / relative).resolve()
            path.relative_to(bundle)
            return path.read_bytes()
        compressed = read(item['archive'])
        if digest(compressed) != item['gzip_sha256']:
            raise ValueError(f'Compressed archive checksum mismatch: {name}')
        size = item['archive_bytes']
        if type(size) is not int or not 0 < size <= 512 * 1024 * 1024:
            raise ValueError('Archive declared size exceeds supported limit')
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            raw = stream.read(size + 1)
        if len(raw) != item['archive_bytes'] or digest(raw) != item['archive_sha256']:
            raise ValueError(f'Archive checksum mismatch: {name}')
        build = read(item['build_json'])
        if digest(build) != item['build_json_sha256']:
            raise ValueError(f'Build recipe checksum mismatch: {name}')
        recipe = json.loads(build)
        relative = PurePosixPath(recipe['analysis_input']['path'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):
            raise ValueError('Unsafe archive destination')
        folder = out / name
        archive = folder.joinpath(*relative.parts)
        archive.parent.mkdir(parents=True)
        archive.write_bytes(raw)
        (folder / 'build.json').write_bytes(build)
        if not item.get('legacy'):
            content = read(name + '/archive.manifest.json')
            if digest(content) != item['sidecar_sha256']:
                raise ValueError('Sidecar checksum mismatch')
            archive.with_name(archive.stem + '.manifest.json').write_bytes(content)
            if item.get('toolchain_sha256'):
                content = read(name + '/toolchain.json')
                if digest(content) != item['toolchain_sha256']:
                    raise ValueError('Toolchain checksum mismatch')
                (folder / 'build_result.json').write_bytes(content)
        plan.append({'repo_id': name, 'archive': str(archive), 'build_json': str(folder / 'build.json'),
                     'legacy': item.get('legacy', False), 'target_roots': item.get('target_roots', [])})
    (out / 'archive_plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    print(f'Verified and unpacked {len(plan)} repositories. Plan: {out / "archive_plan.json"}')


if __name__ == '__main__':
    main()

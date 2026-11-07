"""Select explicit production roots and their compiler-resolved import closure."""
from pathlib import PurePosixPath
import copy

NONPRODUCTION = {'test', 'tests', 'mock', 'mocks', 'script', 'scripts'}


def production_archive(data, roots):
    result = copy.deepcopy(data)
    project = PurePosixPath(data['working_dir'])
    removed = []
    keep_sources = set()
    units = {}
    for name, unit in result['compilation_units'].items():
        sources = unit['source_units']
        by_id = {s['ast']['id']: key for key, s in sources.items()}
        absolute = {}
        for key in sources:
            matches = [f['absolute'] for f in unit['filenames'] if key in f.values()]
            if len(set(matches)) != 1:
                raise ValueError(f'Ambiguous source identity: {key}')
            absolute[key] = matches[0]
        selected = set()
        for key, path in absolute.items():
            try:
                relative = PurePosixPath(path).relative_to(project)
            except ValueError:
                continue  # external dependencies can only enter via imports
            if any(relative == PurePosixPath(r) or PurePosixPath(r) in relative.parents for r in roots):
                if not NONPRODUCTION.intersection(relative.parts[:-1]) and not relative.name.endswith(('.t.sol', '.s.sol')):
                    selected.add(key)
        pending = list(selected)
        while pending:
            key = pending.pop()
            for node in sources[key]['ast'].get('nodes', []):
                if node.get('nodeType') != 'ImportDirective':
                    continue
                target = by_id.get(node.get('sourceUnit'))
                if target is None:
                    raise ValueError(f'Archive is missing imported AST: {key}: {node}')
                if target not in selected:
                    selected.add(target)
                    pending.append(target)
        removed += [absolute[k] for k in sources if k not in selected]
        if selected:
            unit['source_units'] = {k: v for k, v in sources.items() if k in selected}
            kept = {absolute[k] for k in selected}
            unit['filenames'] = [f for f in unit['filenames'] if f['absolute'] in kept]
            keep_sources.update(kept)
            units[name] = unit
    if not units:
        raise ValueError('No compiled sources matched explicit production roots')
    result['compilation_units'] = units
    result['source_content'] = {k: v for k, v in data['source_content'].items() if k in keep_sources}
    return result, {'production_roots': roots, 'excluded_unreachable_sources': sorted(set(removed) - keep_sources),
                    'policy': 'explicit-roots-plus-solc-import-closure-v1'}

"""Container export of captured compiler outputs, including contract-free ASTs."""
import json
import copy
import os
from pathlib import Path
import sys
from crytic_compile import CryticCompile
from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.platform.solc_standard_json import SolcStandardJson, parse_standard_json_output
from crytic_compile.platform.archive import generate_archive_export

captures = [json.loads(p.read_text()) for p in Path(sys.argv[1]).glob('*.json')]
if not captures:
    raise ValueError('No captures')
root = Path('/tmp/gptscan-context').resolve()
for value in captures:
    for name, content in value.get('output_source_content', {}).items():
        path = Path(name).resolve()
        path.relative_to(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text() != content:
            raise ValueError(f'Conflicting compiler source: {name}')
        path.write_text(content)
    for name, source in value['input']['sources'].items():
        if 'content' not in source:
            raise ValueError('Capture is not self-contained')
        path = (Path(value['working_dir']) / name).resolve()
        path.relative_to(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text() != source['content']:
            raise ValueError(f'Conflicting captured source: {path}')
        path.write_text(source['content'])


class Captured(SolcStandardJson):
    def compile(self, cc, **kwargs):
        for index, value in enumerate(captures):
            contracts = [c for cs in value['output'].get('contracts', {}).values() for c in cs.values()]
            if contracts and not any('evm' in c for c in contracts):
                declarations = [n for s in value['output']['sources'].values() for n in s['ast'].get('nodes', [])
                                if n.get('nodeType') == 'ContractDefinition']
                if not declarations or any(n.get('contractKind') != 'interface' for n in declarations):
                    raise ValueError('Non-interface capture missing bytecode')
                continue  # Brownie's final ABI-only interface pass, not executable code
            unit = CompilationUnit(cc, f'{value["version"]}-{index}')
            unit.compiler_version = CompilerVersion(compiler='solc', version=value['version'],
                                                    optimized=value['input']['settings']['optimizer']['enabled'])
            output = copy.deepcopy(value['output'])
            filenames = {name: str((Path(value['working_dir']) / name).resolve()) for name in output['sources']}
            def paths(node):
                if isinstance(node, dict):
                    if node.get('absolutePath') in filenames:
                        node['absolutePath'] = filenames[node['absolutePath']]
                    for child in node.values():
                        paths(child)
                elif isinstance(node, list):
                    for child in node:
                        paths(child)
            paths(output)
            output['sources'] = {filenames[name]: source for name, source in output['sources'].items()}
            output['contracts'] = {filenames[name]: contracts for name, contracts in output.get('contracts', {}).items()}
            parse_standard_json_output(output, unit, solc_working_dir=value['working_dir'])


os.chdir(root / 'source')
cc = CryticCompile(Captured({}))
archive, _ = generate_archive_export(cc)
out = Path(sys.argv[2])
out.mkdir(exist_ok=False)
(out / 'brownie_complete_export_archive.json').write_text(json.dumps(archive))
print('Complete Brownie compiler archive exported without recompiling')

"""Container-only baseline build: preserve compiler context; scope reports later.

Uses a trusted existing recipe and runner helpers. Does not claim production-v1
scope validation: output is imported explicitly with source comparison instead.
Original repository is read-only; commands execute on an ephemeral copy.
"""
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    sys.path.insert(0, '/reusable')
    spec = importlib.util.spec_from_file_location('context_runner', '/reusable/scripts/docker_repo_runner.py')
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    build = json.loads(Path('/recipe/build.json').read_text())
    out = Path('/result')
    work = Path('/tmp/gptscan-context/source')
    runner.copy_source(Path('/original'), work)
    project = work / build['source'].get('working_directory', '.')
    env = runner.node_environment(os.environ, runner.selected_node_version(build, None))
    env = runner.apply_cache_environment(runner.apply_build_environment(env, build))
    # Avoid the optimizing JS JIT path that crashed under amd64 emulation.
    # Unlike --jitless, --no-opt keeps WebAssembly available to solc-js.
    actual_node = shutil.which('node', path=env['PATH'])
    wrapper_dir = Path('/tmp/gptscan-node-safe')
    wrapper_dir.mkdir(exist_ok=True)
    wrapper = wrapper_dir / 'node'
    wrapper.write_text(f'#!/bin/sh\nexec "{actual_node}" --no-opt --no-sparkplug --liftoff-only --no-wasm-tier-up "$@"\n')
    wrapper.chmod(0o755)
    env['PATH'] = str(wrapper_dir) + ':' + env['PATH']
    env['HOME'] = '/tmp/gptscan-context/home'
    Path(env['HOME']).mkdir(parents=True)
    runner.prepare_solc_select_home(env)
    records = []
    log = out / 'build.log'
    if build['framework'] == 'brownie':
        solcx = Path('/tmp/gptscan-solcx')
        solcx.mkdir(exist_ok=True)
        bounded = {tuple(map(int, m.groups())) for c in build['toolchain']['solidity'].get('pragma_constraints', [])
                   for m in re.finditer(r'\^\s*(\d+)\.(\d+)\.', c['expression'])}
        selected = []
        available = list(runner.SHARED_SOLC_SELECT_ROOT.glob('artifacts/solc-*/solc-*'))
        for minor in bounded:
            candidates = [b for b in available if tuple(map(int, b.name.removeprefix('solc-').split('.')[:2])) == minor]
            if candidates:
                selected.append(max(candidates, key=lambda b: tuple(map(int, b.name.removeprefix('solc-').split('.')))))
        if not selected:
            raise ValueError('Brownie requires reviewed compiler constraints; no bounded pragma candidates')
        for binary in selected:
            link = solcx / ('solc-v' + binary.name.removeprefix('solc-'))
            if not link.exists():
                link.symlink_to(binary)
        env['SOLCX_BINARY_PATH'] = str(solcx)
        venv = Path('/cache/gptscan-brownie-1.21.0')
        if not (venv / 'bin/brownie').exists():
            subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
            runner.run_command(stage='brownie-environment', argv=[str(venv / 'bin/pip'), 'install', 'eth-brownie==1.21.0'],
                               cwd=project, environment=env, log_path=log, records=records)
        runner.run_command(stage='brownie-environment', argv=[str(venv / 'bin/pip'), 'install', 'setuptools==75.8.0'],
                           cwd=project, environment=env, log_path=log, records=records)
        env['PATH'] = str(venv / 'bin') + ':' + env['PATH']
    runner.materialize_adapter_files(project, build)
    for c in build['setup']['commands']:
        runner.run_command(stage='setup', argv=c['argv'], cwd=project, environment=env, log_path=log, records=records)
    runner.prefetch_hardhat_compilers(build=build, project_dir=project, environment=env, log_path=log, records=records)
    for c in build['compile']['commands']:
        argv = c['argv']
        if build['framework'] == 'brownie' and argv[0] == 'brownie':
            argv = [str(venv / 'bin/python'), '/brownie_capture.py', *argv[1:]]
        runner.run_command(stage='compile', argv=argv, cwd=project, environment=env, log_path=log, records=records)
    framework = build['framework']
    flags = {'foundry': '--foundry-ignore-compile', 'hardhat': '--hardhat-ignore-compile',
             'truffle': '--truffle-ignore-compile', 'brownie': '--brownie-ignore-compile'}
    command = ['crytic-compile', '.', '--compile-force-framework', framework, flags[framework],
               '--export-format', 'archive', '--export-dir', '/result/export']
    command += runner.analysis_input_arguments(build)
    if framework == 'brownie':
        runner.run_command(stage='archive', argv=[sys.executable, '/export_brownie_capture.py',
                           '/result/compiler-capture', '/result/export'], cwd=project, environment=env,
                           log_path=log, records=records)
    else:
        runner.run_command(stage='archive', argv=command, cwd=project, environment=env, log_path=log, records=records)
    save = {'repo_id': build['repo_id'], 'compiler_context_policy': 'baseline-framework-inputs-v1',
            'production_scope_validated': False, 'commands': records,
            'node_argv': [actual_node, '--no-opt', '--no-sparkplug', '--liftoff-only', '--no-wasm-tier-up'],
            'note': 'Compiler keeps dependencies/tests required by framework; report targets filtered separately.'}
    (out / 'context_build.json').write_text(json.dumps(save, indent=2))


if __name__ == '__main__':
    main()

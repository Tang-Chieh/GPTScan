"""Capture complete successful solc output; do not change Brownie decisions."""
import json
from pathlib import Path
import sys
import solcx

original = solcx.compile_standard


def capture(input_data, *args, **kwargs):
    output = original(input_data, *args, **kwargs)
    folder = Path('/result/compiler-capture')
    folder.mkdir(exist_ok=True)
    version = str(solcx.get_solc_version())
    path = folder / f'{version}-{len(list(folder.glob("*.json")))}.json'
    sources = {}
    for name in output.get('sources', {}):
        source = (Path.cwd() / name).resolve()
        if not source.is_file() or source.suffix != '.sol':
            raise ValueError(f'Cannot capture compiler source bytes: {source}')
        sources[str(source)] = source.read_text()
    path.write_text(json.dumps({'version': version, 'working_dir': str(Path.cwd()), 'input': input_data,
                                'output': output, 'output_source_content': sources}))
    return output


solcx.compile_standard = capture
from brownie._cli.__main__ import main
sys.argv = ['brownie', *sys.argv[1:]]
main()

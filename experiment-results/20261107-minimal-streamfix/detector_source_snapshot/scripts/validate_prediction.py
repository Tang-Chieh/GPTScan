"""Validate against YOUR actual benchmark_eval/contract.py, without invoking Judge."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-file", type=Path, required=True,
                        help="Trusted local src/benchmark_eval/contract.py")
    parser.add_argument("--prediction", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("gptscan_benchmark_contract", args.contract_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    result = module.PredictionCase.model_validate(json.loads(args.prediction.read_text()))
    print(f"PredictionCase validated: {result.repo_id}, {len(result.predictions)} predictions")


if __name__ == "__main__":
    main()

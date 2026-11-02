"""Two short live requests using GPTScan's own transport; consumes plan usage."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from model_transport import send


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--gateway-url", default="http://127.0.0.1:4000/v1")
    parser.add_argument("--model", default="openai-codex/gpt-5.6-luna")
    args = parser.parse_args()
    os.environ.update(GPTSCAN_PROVIDER="codex-gateway", GPTSCAN_MODEL=args.model,
                      GPTSCAN_BASE_URL=args.gateway_url,
                      GPTSCAN_GATEWAY_TOKEN_FILE=str(args.token_file.resolve()))
    import json
    system = {"role": "system", "content": "Follow the exact output format; no markdown."}
    answer = send([system, {"role": "user", "content": "Reply exactly yes"}])
    if answer.strip().lower() != "yes":
        raise ValueError("Yes/no parser smoke failed")
    answer = send([system, {"role": "user", "content": 'Reply exactly {"1":"yes","2":"no"}'}])
    if json.loads(answer) != {"1": "yes", "2": "no"}:
        raise ValueError("JSON parser smoke failed")
    print(f"Gateway smoke passed: {args.model} (yes/no + JSON)")


if __name__ == "__main__":
    main()

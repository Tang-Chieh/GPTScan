#!/usr/bin/env python3
"""Install the pinned OMP binary or pass commands to its auth broker/gateway."""
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSION = "18.6.0"
HASHES = {
    "omp-darwin-arm64": "bf7f20fbe3a41f3fae9cb3f8c5bfe52797ced272db7c91a205b0abf91f144f15",
    "omp-darwin-x64": "9b45e98a1c9436f89a8459b89efb9e26075edbb0cead95423b3f4f19a80d00eb",
    "omp-linux-arm64": "542083fe42a6169565861a4ee9118fbed64d09c93468b6907e6016cc76ef00d1",
    "omp-linux-x64": "844c640c620ec4c152abe4b3736049f963205da50e9e77bd9bdf2a981a6ead55",
}


def asset():
    system = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "AMD64": "x64"}.get(platform.machine())
    name = f"omp-{system}-{arch}"
    if name not in HASHES:
        raise ValueError("Installer supports macOS/Linux glibc ARM64/x64; use a supported host")
    return name


def main():
    args = sys.argv[1:]
    binary = ROOT / ".local/bin/omp"
    if args == ["install"]:
        name = asset()
        binary.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(f"https://github.com/can1357/oh-my-pi/releases/download/v{VERSION}/{name}", timeout=120) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != HASHES[name]:
            raise ValueError("Downloaded OMP checksum differs from pinned release checksum")
        binary.write_bytes(content)
        binary.chmod(0o755)
        print(f"Installed OMP {VERSION}: {binary}")
        return 0
    if not args or args == ["--help"]:
        print("python scripts/gateway.py install\npython scripts/gateway.py auth-broker login openai-codex\npython scripts/gateway.py auth-broker serve\npython scripts/gateway.py auth-gateway serve --bind=127.0.0.1:4000")
        return 0
    if not binary.is_file():
        raise ValueError("Run python scripts/gateway.py install first")
    if hashlib.sha256(binary.read_bytes()).hexdigest() != HASHES[asset()]:
        raise ValueError("Installed gateway binary does not match pinned OMP release")
    env = os.environ.copy()
    env["PI_CONFIG_DIR"] = os.path.relpath(ROOT / ".local/omp", Path.home())
    env["PI_CODING_AGENT_DIR"] = str(ROOT / ".local/omp/agent")
    # The native loader may use ~/.omp/natives; credentials use the isolated config directory.
    if args[0] == "auth-gateway":
        env.setdefault("OMP_AUTH_BROKER_URL", "http://127.0.0.1:8765")
    for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        env.pop(key, None)
    return subprocess.call([str(binary), *args], env=env, cwd=ROOT)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"Gateway error: {exc}", file=sys.stderr)
        raise SystemExit(2)

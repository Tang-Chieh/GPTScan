"""Explicit detection scope; not post-hoc filtering of general findings."""
from pathlib import Path

PRICE_RULE_FILES = ("Flashloan_Price.yml", "OraclePrice.yml")


def rule_paths(directory, profile):
    root = Path(directory)
    if profile == "price":
        return [root / name for name in PRICE_RULE_FILES]
    if profile == "general":
        return sorted(path for path in root.glob("*.yml") if path.name != "OraclePrice.yml")
    raise ValueError("Unknown detection profile")

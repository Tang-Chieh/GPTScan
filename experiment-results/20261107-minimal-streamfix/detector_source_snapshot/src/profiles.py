"""Explicit detection scope; not post-hoc filtering of general findings."""
from pathlib import Path

PRICE_RULE_FILES = (
    "Flashloan_Price.yml", "FirstDeposit.yml", "Flashloan_Buy.yml",
    "Flashloan_Vote.yml", "FrontRun.yml", "WrongOrder_Checkpoint.yml",
    "WrongOrder_Interest.yml",
)


def rule_paths(directory, profile):
    root = Path(directory)
    if profile == "price":
        return [root / name for name in PRICE_RULE_FILES]
    if profile == "general":
        return sorted(root.glob("*.yml"))
    raise ValueError("Unknown detection profile")

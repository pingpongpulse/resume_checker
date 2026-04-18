"""Interactive terminal REPL for skill similarity checks."""

from __future__ import annotations

from pathlib import Path
import importlib.util
import sys


def _load_utils_module():
    script_dir = Path(__file__).resolve().parent
    utils_path = script_dir / "utils.py"

    spec = importlib.util.spec_from_file_location("utils", utils_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load utils module from {utils_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_pair(raw: str):
    raw = raw.strip()
    if not raw:
        return None

    for sep in [",", "|", "->", ":"]:
        if sep in raw:
            left, right = raw.split(sep, 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                return left, right
            return None

    return None


def main() -> int:
    utils = _load_utils_module()

    print("Skill Similarity Live Terminal")
    print("Type pairs as: skill_a, skill_b")
    print("Also supported separators: |  ->  :")
    print("Type 'q' to quit")

    while True:
        try:
            raw = input("pair> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return 0

        if raw.strip().lower() in {"q", "quit", "exit"}:
            print("Exiting.")
            return 0

        pair = _parse_pair(raw)
        if pair is None:
            print("Invalid format. Example: flask, django")
            continue

        skill_a, skill_b = pair
        try:
            score = utils.skill_similarity(skill_a, skill_b)
        except FileNotFoundError as exc:
            print(exc)
            print("Train the model first from the notebook training cell.")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            continue

        print(f"similarity({skill_a}, {skill_b}) = {score}")


if __name__ == "__main__":
    sys.exit(main())

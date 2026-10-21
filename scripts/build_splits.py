"""Writes data/splits/v1.json (frozen in F1-T13; do not regenerate after freezing)."""

import os

from wafarena.splits.builder import write_splits


def main() -> None:
    write_splits(os.environ.get("VERIFIED_COMMIT", "unknown"))
    print("wrote data/splits/v1.json")


if __name__ == "__main__":
    main()

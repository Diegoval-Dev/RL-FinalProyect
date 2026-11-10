"""Check that every decimal figure in the report chapters appears in results/summary."""

import csv
import glob
import json
import re
import sys

SUMMARY_GLOB = "results/summary/*"
CHAPTER_GLOBS = ("report/capitulos/0[4-7]*.md", "report/capitulos/09-conclusiones.md")
NUMBER_PATTERN = re.compile(r"-?\d+\.\d+|-?\d+")
REPORT_DECIMAL_PATTERN = re.compile(r"(?<![\w.])\d+,\d{2,}")
TOLERANCE = 1e-9
# Means of the 84 per-condition TPR rows in EXP-I1_history.csv (naive 0.9810, pool 0.9841).
DERIVED_FIGURES = {"0,9810", "0,9841"}


def summary_numbers() -> list[float]:
    numbers: list[float] = []
    for path in glob.glob(SUMMARY_GLOB):
        if path.endswith(".csv"):
            with open(path, newline="") as handle:
                text = " ".join(cell for row in csv.reader(handle) for cell in row)
        elif path.endswith(".json"):
            text = json.dumps(json.load(open(path)))
        else:
            continue
        numbers.extend(float(token) for token in NUMBER_PATTERN.findall(text))
    return numbers


def is_backed(token: str, numbers: list[float]) -> bool:
    decimals = len(token.split(",")[1])
    value = float(token.replace(",", "."))
    return any(
        abs(round(number, decimals) - value) < TOLERANCE
        or abs(round(number * 100, decimals) - value) < TOLERANCE
        for number in numbers
    )


def unbacked_figures(numbers: list[float]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    paths = sorted(path for pattern in CHAPTER_GLOBS for path in glob.glob(pattern))
    for path in paths:
        text = open(path).read()
        text = re.sub(r"\]\([^)]*\)|`[^`]*`", "", text)
        tokens = {m.group(0) for m in REPORT_DECIMAL_PATTERN.finditer(text)}
        bad = sorted(t for t in tokens if t not in DERIVED_FIGURES and not is_backed(t, numbers))
        if bad:
            missing[path] = bad
    return missing


if __name__ == "__main__":
    result = unbacked_figures(summary_numbers())
    for chapter, tokens in result.items():
        print(chapter, tokens)
    sys.exit(1 if result else 0)

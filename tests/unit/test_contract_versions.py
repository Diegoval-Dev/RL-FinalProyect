"""F1-T01: contract versions are exposed by the package."""

import re
from pathlib import Path

import wafarena

CONTRACTS_README = Path(__file__).parents[2] / "docs" / "02-contratos" / "README.md"
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")


def documented_contract_names() -> set[str]:
    return set(re.findall(r"\[([\w-]+)\.md\]\(\1\.md\)", CONTRACTS_README.read_text()))


def test_contract_versions_expose_all_contracts_returns_nine_entries():
    assert len(wafarena.CONTRACT_VERSIONS) == 9


def test_contract_versions_match_documented_contract_names():
    assert set(wafarena.CONTRACT_VERSIONS) == documented_contract_names()


def test_contract_versions_use_major_minor_format():
    assert all(VERSION_PATTERN.match(v) for v in wafarena.CONTRACT_VERSIONS.values())

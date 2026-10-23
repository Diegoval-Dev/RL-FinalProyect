"""F2-T03: run identity, results tree, uncommitted-changes guard and meta.yaml."""

import subprocess
from pathlib import Path

import pytest
import yaml

import wafarena
from wafarena import runmeta


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "work")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    for folder in ("wafarena", "configs", "docs"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "file.txt").write_text("v1")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_git_info_reports_short_sha_and_branch(repo):
    info = runmeta.git_info(repo)
    assert info.branch == "work"
    assert info.sha == git(repo, "rev-parse", "--short=7", "HEAD")
    assert len(info.sha) == 7


def test_run_id_follows_the_contract():
    assert (
        runmeta.run_id("EXP-D1", "qlearning-pl1", 3, "abc1234")
        == "EXP-D1__qlearning-pl1__s3__abc1234"
    )


def test_run_dir_follows_the_results_tree(tmp_path):
    path = runmeta.run_dir(tmp_path, "EXP-D1", "qlearning-pl1", 3)
    assert path == tmp_path / "EXP-D1" / "qlearning-pl1" / "s3"


def test_clean_tree_passes_the_guard(repo):
    assert runmeta.uncommitted_changes(repo) == []
    runmeta.ensure_clean(repo, allow_dirty=False)


@pytest.mark.parametrize("folder", ["wafarena", "configs"])
def test_modified_guarded_file_blocks_the_run(repo, folder):
    (repo / folder / "file.txt").write_text("v2")
    with pytest.raises(runmeta.DirtyTreeError, match=folder):
        runmeta.ensure_clean(repo, allow_dirty=False)


def test_untracked_file_in_guarded_folder_blocks_the_run(repo):
    (repo / "configs" / "new.yaml").write_text("x: 1")
    with pytest.raises(runmeta.DirtyTreeError, match="new.yaml"):
        runmeta.ensure_clean(repo, allow_dirty=False)


def test_changes_outside_guarded_folders_are_ignored(repo):
    (repo / "docs" / "file.txt").write_text("v2")
    runmeta.ensure_clean(repo, allow_dirty=False)


def test_allow_dirty_lets_the_run_proceed(repo):
    (repo / "wafarena" / "file.txt").write_text("v2")
    runmeta.ensure_clean(repo, allow_dirty=True)


def test_meta_records_provenance(repo):
    config = {"exp_id": "EXP-D1", "run_name": "q", "seeds": [3]}
    meta = runmeta.build_meta(config, seed=3, repo=repo, allow_dirty=False)
    assert meta["run_id"] == f"EXP-D1__q__s3__{runmeta.git_info(repo).sha}"
    assert meta["git_sha"] == runmeta.git_info(repo).sha
    assert meta["branch"] == "work" and meta["seed"] == 3
    assert meta["allow_dirty"] is False
    assert meta["contract_versions"] == wafarena.CONTRACT_VERSIONS
    assert {"date", "machine", "python"} <= meta.keys()


def test_dirty_runs_are_marked_in_meta(repo):
    (repo / "wafarena" / "file.txt").write_text("v2")
    config = {"exp_id": "EXP-D1", "run_name": "q", "seeds": [3]}
    meta = runmeta.build_meta(config, seed=3, repo=repo, allow_dirty=True)
    assert meta["allow_dirty"] is True and meta["dirty"] is True


def test_write_and_finalize_meta(tmp_path):
    runmeta.write_meta(tmp_path, {"run_id": "r"})
    assert yaml.safe_load((tmp_path / "meta.yaml").read_text()) == {"run_id": "r"}
    runmeta.finalize_meta(tmp_path, duration_s=12.5)
    assert yaml.safe_load((tmp_path / "meta.yaml").read_text()) == {
        "run_id": "r",
        "duration_s": 12.5,
    }

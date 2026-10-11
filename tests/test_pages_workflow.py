"""Check workflow repairs across filenames and GitHub Actions run styles."""
import pytest

from tools.repair_pages_workflow import repair_text, repair_workflows


@pytest.mark.parametrize("run", [
    "        run: python tools/check_distribution.py dist\n",
    '        run: "python tools/check_distribution.py dist"\n',
    "        run: |\n          python tools/check_distribution.py dist\n",
    "        run: python3 tools/check_distribution.py dist\n",
])
def test_fix_runs_before_check_in_supported_run_styles(run):
    fixed, found = repair_text(run)
    assert found
    assert fixed.index("tools/fix_web_paths.py") < fixed.index("tools/check_distribution.py")
    assert " && " in fixed
    assert repair_text(fixed) == (fixed, True)


def test_comments_and_other_workflow_commands_are_preserved():
    text = "# run: python tools/check_distribution.py dist\nrun: python -m pytest -q\n"
    assert repair_text(text) == (text, False)


def test_any_workflow_filename_is_repaired_and_other_files_stay_intact(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/fix_web_paths.py").write_text("# included helper\n")
    folder = tmp_path / ".github/workflows"
    folder.mkdir(parents=True)
    for name in ("deploy.yml", "custom-pages.yaml"):
        (folder / name).write_text("run: python tools/check_distribution.py dist\n")
    untouched = folder / "tests.yml"
    untouched.write_text("run: python -m pytest -q\n")
    changes = repair_workflows(tmp_path)
    assert {p.name for p in changes} == {"deploy.yml", "custom-pages.yaml"}
    assert untouched.read_text() == "run: python -m pytest -q\n"
    assert repair_workflows(tmp_path) == []


def test_missing_runtime_helper_fails_without_modifying_files(tmp_path):
    with pytest.raises(ValueError, match="Missing tools/fix_web_paths"):
        repair_workflows(tmp_path)


def test_unrecognized_workflow_fails_without_modifying_files(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/fix_web_paths.py").write_text("# included helper\n")
    folder = tmp_path / ".github/workflows"
    folder.mkdir(parents=True)
    path = folder / "pages.yml"
    original = "run: echo unrelated workflow\n"
    path.write_text(original)
    with pytest.raises(ValueError, match="No packaged-app check"):
        repair_workflows(tmp_path)
    assert path.read_text() == original

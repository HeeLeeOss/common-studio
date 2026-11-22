import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "license_audit.py"
FIXTURES = ROOT / "tests" / "fixtures" / "licence"


def _load_audit():
    spec = importlib.util.spec_from_file_location("license_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses looks the module up by name
    spec.loader.exec_module(module)
    return module


audit_mod = _load_audit()


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_copyleft_fixture_makes_the_audit_fail():
    result = _run("--path", str(FIXTURES / "copyleft"))
    assert result.returncode == 1
    assert "gpl-fixture" in result.stdout
    assert "GPL-3.0-or-later" in result.stdout
    assert "lgpl-classifier-fixture" in result.stdout
    assert "FAIL: copyleft licence" in result.stderr


def test_permissive_fixture_passes_and_lists_every_licence():
    result = _run("--path", str(FIXTURES / "permissive"))
    assert result.returncode == 0
    assert "mit-fixture" in result.stdout
    assert "MIT" in result.stdout
    assert "0 copyleft" in result.stdout


def test_audit_of_the_installed_tree_lists_every_distribution():
    findings = audit_mod.audit()
    names = {f.name.lower() for f in findings}
    assert "pytest" in names
    assert all(f.licence for f in findings)


@pytest.mark.parametrize(
    "licence",
    [
        "GPL-2.0-only",
        "GPL-3.0-or-later",
        "LGPL-2.1-or-later",
        "AGPL-3.0-only",
        "OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "GNU Affero General Public License v3",
        "EUPL-1.2",
        "MPL-2.0",
        "EPL-2.0",
    ],
)
def test_copyleft_licences_are_flagged(licence):
    assert audit_mod.is_copyleft(licence)


@pytest.mark.parametrize(
    "licence",
    ["MIT", "Apache-2.0", "BSD-2-Clause", "Unlicense", "OSI Approved :: MIT License", "PSF-2.0", audit_mod.UNKNOWN],
)
def test_permissive_and_unknown_licences_are_not_flagged(licence):
    assert not audit_mod.is_copyleft(licence)


def test_licence_expression_takes_precedence_over_licence_field_and_classifiers():
    from email.message import Message

    meta = Message()
    meta["License-Expression"] = "MIT"
    meta["License"] = "GPL-3.0"
    meta["Classifier"] = "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    assert audit_mod.licence_of(meta) == "MIT"


def test_licence_field_takes_precedence_over_classifiers_and_uses_first_line_only():
    from email.message import Message

    meta = Message()
    meta["License"] = "BSD-3-Clause\nfull licence text follows\nmore text"
    meta["Classifier"] = "License :: OSI Approved :: GNU General Public License v2 (GPLv2)"
    assert audit_mod.licence_of(meta) == "BSD-3-Clause"


def test_missing_licence_is_reported_as_unknown_and_does_not_fail(tmp_path):
    dist = tmp_path / "bare-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: bare\nVersion: 1.0\n", encoding="utf-8")
    result = _run("--path", str(tmp_path))
    assert result.returncode == 0
    assert "UNKNOWN" in result.stdout

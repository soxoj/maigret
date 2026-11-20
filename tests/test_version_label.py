"""Tests for the banner's version label.

The label exists because the version string alone cannot tell a release from
`main`: both say 0.6.6 while `main` is that release plus a few hundred commits.
A bug report from a git checkout would otherwise name a release that never had
the bug, which is what happened with the Telegram bot: its deployment reported
0.6.3 for four months and nobody could tell it apart from the real 0.6.3.
"""

import importlib.metadata
import json

import pytest

from maigret import notify
from maigret.__version__ import __version__


class _FakeDist:
    """Stands in for importlib.metadata.Distribution: only read_text is used."""

    def __init__(self, raw):
        self._raw = raw

    def read_text(self, name):
        assert name == "direct_url.json"
        return self._raw


@pytest.fixture
def direct_url(monkeypatch):
    """Install a fake direct_url.json payload, or an absent distribution."""

    def _set(raw, missing=False):
        def from_name(name):
            if missing:
                raise importlib.metadata.PackageNotFoundError(name)
            return _FakeDist(raw)

        monkeypatch.setattr(
            importlib.metadata.Distribution, "from_name", staticmethod(from_name)
        )

    return _set


SHA = "408e7b8dfafb0201901a5c71ff204ac521a40c3a"
SHORT = SHA[:7]


# --- the three real install shapes -----------------------------------------


def test_release_install_has_no_suffix(direct_url):
    """A wheel from PyPI carries no direct_url.json at all."""
    direct_url(None)
    assert notify._version_label() == __version__


def test_git_install_appends_the_commit(direct_url):
    direct_url(
        json.dumps(
            {
                "url": "https://github.com/soxoj/maigret",
                "vcs_info": {
                    "vcs": "git",
                    "commit_id": SHA,
                    "requested_revision": "main",
                },
            }
        )
    )
    assert notify._version_label() == f"{__version__}+{SHORT}"


def test_editable_checkout_reads_the_checked_out_commit(direct_url, tmp_path):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text(SHA + "\n", encoding="utf-8")
    direct_url(
        json.dumps({"dir_info": {"editable": True}, "url": f"file://{tmp_path}"})
    )
    assert notify._version_label() == f"{__version__}+{SHORT}"


# --- shapes a real checkout can be in --------------------------------------


def test_worktree_follows_the_gitdir_pointer(direct_url, tmp_path):
    """In a worktree .git is a file pointing at the real gitdir, and that is
    where every release branch of this project is prepared."""
    real = tmp_path / "store" / "worktrees" / "wt"
    (real / "refs" / "heads").mkdir(parents=True)
    (real / "HEAD").write_text("ref: refs/heads/topic\n", encoding="utf-8")
    (real / "refs" / "heads" / "topic").write_text(SHA + "\n", encoding="utf-8")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")
    direct_url(
        json.dumps({"dir_info": {"editable": True}, "url": f"file://{checkout}"})
    )
    assert notify._version_label() == f"{__version__}+{SHORT}"


def test_packed_refs_are_read_when_the_loose_ref_is_gone(direct_url, tmp_path):
    """git gc packs refs away, and then the loose file does not exist."""
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted \n"
        f"deadbeefdeadbeefdeadbeefdeadbeefdeadbeef refs/heads/other\n"
        f"{SHA} refs/heads/main\n",
        encoding="utf-8",
    )
    direct_url(
        json.dumps({"dir_info": {"editable": True}, "url": f"file://{tmp_path}"})
    )
    assert notify._version_label() == f"{__version__}+{SHORT}"


def test_detached_head_is_used_verbatim(direct_url, tmp_path):
    """A detached HEAD holds the sha itself, with no ref to follow."""
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text(SHA + "\n", encoding="utf-8")
    direct_url(
        json.dumps({"dir_info": {"editable": True}, "url": f"file://{tmp_path}"})
    )
    assert notify._version_label() == f"{__version__}+{SHORT}"


# --- everything that must degrade to a plain version -----------------------


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("{not json}", id="broken-json"),
        pytest.param("", id="empty-file"),
        pytest.param(json.dumps({"url": "file:///tmp/x"}), id="no-vcs-no-editable"),
        pytest.param(
            json.dumps({"dir_info": {"editable": True}, "url": "https://example/x"}),
            id="editable-but-not-a-local-path",
        ),
        pytest.param(json.dumps({"vcs_info": {"vcs": "git"}}), id="vcs-without-commit"),
    ],
)
def test_unusable_metadata_degrades_to_the_plain_version(direct_url, raw):
    direct_url(raw)
    assert notify._version_label() == __version__


def test_missing_distribution_degrades_to_the_plain_version(direct_url):
    """Running from a source tree with nothing installed at all."""
    direct_url(None, missing=True)
    assert notify._version_label() == __version__


def test_editable_pointing_at_a_directory_without_git(direct_url, tmp_path):
    direct_url(
        json.dumps({"dir_info": {"editable": True}, "url": f"file://{tmp_path}"})
    )
    assert notify._version_label() == __version__


def test_head_naming_a_ref_that_does_not_exist(direct_url, tmp_path):
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/gone\n", encoding="utf-8")
    direct_url(
        json.dumps({"dir_info": {"editable": True}, "url": f"file://{tmp_path}"})
    )
    assert notify._version_label() == __version__


# --- the label as the user sees it -----------------------------------------


def test_commit_is_shortened_to_seven_characters(direct_url):
    direct_url(json.dumps({"vcs_info": {"vcs": "git", "commit_id": SHA}}))
    label = notify._version_label()
    assert label.endswith("+" + SHA[:7])
    assert SHA not in label


def test_banner_carries_the_version(capsys):
    """INTRO_TEXT is built at import time, so this pins the shape of the line
    rather than the label of whatever install the test runs on."""
    notify.print_intro_banner(no_color=True)
    line = capsys.readouterr().out
    assert "MAIGRET" in line
    assert __version__ in line


def test_git_head_handles_an_unreadable_gitdir(tmp_path):
    assert notify._git_head(str(tmp_path / "nope")) == ""

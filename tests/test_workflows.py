"""Guards for the release-publishing GitHub Actions workflow.

Regression tests for #2959. The PyInstaller development build used to publish
itself with ``makeLatest: true`` under a tag named after the branch it was built
from, which caused three separate problems:

1. the Windows dev build held the repository's "Latest release" marker ahead of
   every stable release, and stole it back on every push to ``main``;
2. the tag never moved, so it kept naming the first build while the attached
   ``.exe`` was replaced on every push;
3. the tags ``main`` / ``dev`` shadowed the branches of the same name, making a
   bare ``main`` refname ambiguous in every clone.

These tests read the workflow as data, so they fail if any of the three
conditions is reintroduced.

The workflow also attaches the binary to releases a human publishes, which is a
second ``release-action`` step with the opposite requirements: it must not touch
the title, the notes or the prerelease flag that the publisher chose. Both steps
are covered below, and each must stay guarded on a specific ``github.event_name``
so neither ever runs on the other's event.
"""

import os

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    ".github",
    "workflows",
    "pyinstaller.yml",
)

RELEASE_ACTION = "ncipollo/release-action"


@pytest.fixture(scope="module")
def workflow():
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _release_action_steps(workflow):
    steps = workflow["jobs"]["build"]["steps"]
    return [s for s in steps if RELEASE_ACTION in s.get("uses", "")]


def _only_step_for_event(workflow, event):
    matching = [
        s
        for s in _release_action_steps(workflow)
        if f"github.event_name == '{event}'" in s.get("if", "")
    ]
    assert len(matching) == 1, (
        f"expected exactly one {RELEASE_ACTION} step guarded on the {event!r} "
        f"event, found {len(matching)}"
    )
    return matching[0]


@pytest.fixture(scope="module")
def release_step(workflow):
    """The nightly development release, published on every push to a branch."""
    return _only_step_for_event(workflow, "push")


@pytest.fixture(scope="module")
def published_release_step(workflow):
    """The step attaching the binary to a release a human published."""
    return _only_step_for_event(workflow, "release")


def _push_branches(workflow):
    # PyAML resolves the bare `on` key to the boolean True (YAML 1.1 treats it as
    # a truthy literal), so accept either spelling.
    triggers = workflow.get("on", workflow.get(True))
    return triggers["push"]["branches"]


def _resolve(expression, workflow, branch):
    """Expand the workflow-level env and `github.ref_name` in an expression."""
    for name, value in (workflow.get("env") or {}).items():
        expression = expression.replace("${{ env.%s }}" % name, str(value))
    return expression.replace("${{ github.ref_name }}", branch)


def test_dev_build_is_a_prerelease(release_step):
    # Keeps the build out of /releases/latest and out of the `release: released`
    # event that publishes to PyPI.
    assert str(release_step["with"]["prerelease"]).lower() == "true"


def test_dev_build_never_claims_the_latest_marker(release_step):
    assert str(release_step["with"]["makeLatest"]).lower() == "false"


def test_release_tag_does_not_shadow_a_branch(workflow, release_step):
    tag = release_step["with"]["tag"]
    for branch in _push_branches(workflow):
        resolved = _resolve(tag, workflow, branch)
        assert resolved != branch, (
            f"tag {resolved!r} shadows the {branch!r} branch: a bare "
            f"{branch!r} refname would resolve to the tag in every clone"
        )
        assert resolved, f"tag resolved to an empty string for branch {branch!r}"


def test_release_tag_is_moved_to_the_built_commit(workflow, release_step):
    # release-action only creates a tag when it is missing, and GitHub ignores
    # target_commitish for an existing tag, so an explicit push is what keeps the
    # tag in step with the attached binary.
    tag = release_step["with"]["tag"]
    scripts = [s["run"] for s in workflow["jobs"]["build"]["steps"] if "run" in s]
    moves_tag = any(
        "refs/tags/" in script and "--force" in script for script in scripts
    )
    assert moves_tag, (
        f"no step force-pushes {tag!r}; without it the tag stays pinned to the "
        "first build while the release keeps getting new binaries"
    )
    assert workflow.get("permissions", {}).get("contents") == "write"


def test_every_release_step_is_guarded_by_event(workflow):
    # An unguarded step would run on both events: on a published release it
    # would mint a junk nightly-vX.Y.Z tag, and on a push it would try to
    # update a release that does not exist.
    for step in _release_action_steps(workflow):
        assert "github.event_name" in step.get("if", ""), (
            f"{step.get('name')!r} is not guarded by event and would run on both"
        )


def test_published_release_keeps_the_metadata_it_was_given(published_release_step):
    # Whoever published the release chose its title, notes, prerelease and draft
    # state. release-action replaces all four with its own defaults while
    # updating unless every omit is set, so this step must only add the asset.
    options = published_release_step["with"]
    for key in (
        "omitNameDuringUpdate",
        "omitBodyDuringUpdate",
        "omitPrereleaseDuringUpdate",
        "omitDraftDuringUpdate",
    ):
        assert str(options.get(key)).lower() == "true", (
            f"{key} is not set; publishing would overwrite the release notes"
        )


def test_published_release_targets_the_published_tag(published_release_step):
    # NIGHTLY_TAG expands to `nightly-v0.6.6` on a release event, so the step
    # has to name the tag from the event payload instead.
    tag = published_release_step["with"]["tag"]
    assert "github.event.release.tag_name" in tag, (
        f"expected the published tag, got {tag!r}"
    )

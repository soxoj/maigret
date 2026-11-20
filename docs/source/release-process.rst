.. _release-process:

Release process
===============

This page describes how a Maigret release is cut, what each git tag in the
repository means, and which automation reacts to what. It is written for
maintainers and for downstream packagers who need to know which ref to build
from.

Where the version lives
-----------------------

The version is stored in three files and all three have to be changed
together:

- ``pyproject.toml``, the ``version`` field under ``[tool.poetry]``
- ``maigret/__version__.py``, the ``__version__`` string
- ``docs/source/conf.py``, the ``release`` field. Its neighbour
  ``version`` holds the short ``major.minor`` and only moves on a minor
  bump.

``maigret/__version__.py`` is what the snap packaging reads through
``craftctl set version``, and ``pyproject.toml`` is what ends up in the PyPI
metadata. A mismatch between them produces a package that reports one version
and is published as another.

Cutting a release
-----------------

1. Branch off ``main``. The branch is normally named after the version, for
   example ``0.6.5``.
2. Bump the two version files on that branch.
3. Open a pull request for the bump, so the change is reviewed like any other.

The release branch is where the tag will live. It is deliberately separate from
``main``: the tag has to point at a commit whose version files already say the
new number, and ``main`` only receives that commit after the release is out.

Publishing
----------

Create a GitHub Release whose tag is ``vX.Y.Z`` and whose target is the release
branch. Publishing it is the event that starts everything else, so the release
notes should be finished before you publish rather than after.

Two workflows listen for ``release: types: [published]``:

- ``python-publish.yml`` builds the source distribution and the wheel and
  uploads them to PyPI through trusted publishing.
- ``pyinstaller.yml`` builds ``maigret_standalone.exe`` on a Windows runner and
  attaches it to the release. The binary appears a few minutes after the
  release itself.

``python-publish.yml`` builds the released code: it checks out the tag and
packages the checkout.

``pyinstaller.yml`` does the same **since November 2026**, and the history is
worth keeping because the failure mode was invisible. Before #3380 the first
line of ``pyinstaller/requirements.txt`` installed maigret from
``https://github.com/soxoj/maigret/archive/refs/heads/main.zip``, so the job
checked out the tag and then fetched maigret itself from the head of ``main``
over the network. The exe attached to a release held whatever ``main`` held at
build time. For ``v0.6.6`` the two coincided by luck, because at build time the
head of ``main`` was the squashed version bump. The same change moved the build
off Wine onto a Windows runner, added a smoke test, and started installing the
``pdf`` extra, without which the ``-P`` flag raised ``RuntimeError`` in every
standalone build the project had ever shipped.

The snap still has a version-labelling problem of its own.
``snap/snapcraft.yaml`` carries ``adopt-info: maigret`` and takes the version
from ``maigret/__version__.py``, and that file does not change between
releases, so **any snap built from ``main`` between two releases is labelled
with the previous release's version**. It happened: the ``0.6.6`` snap shipped
as two different programs, amd64 built from the tag with 5897 sites, arm64
built six weeks later from ``main`` with 8144 sites and five engines that are
not in the release. The store shows one version string for both and no content
at all, so the mismatch is invisible from outside.

Hence the cheap check, worth running before publishing any artifact: count the
sites inside the thing you just built and compare with the tag.

.. code-block:: console

  git show vX.Y.Z:maigret/resources/data.json | python3 -c \
    'import sys,json; print(len(json.load(sys.stdin)["sites"]))'

For the exe the archive's table of contents is plain text, so the bundled
dependency versions can be read without unpacking:

.. code-block:: console

  grep -aoP '[\w.-]+-[0-9][\w.]*\.dist-info' maigret_standalone.exe | sort -u

Rebuilding an artifact in place is still not a way to refresh it. The attach
step runs with ``replacesArtifacts: true``, so a rebuild overwrites the file on
the release page without a trace, and for the snap the rebuild would also carry
the previous release's version number. Cutting a new release is the honest way
to ship new dependencies.

.. note::
   The ``pypi`` environment has no protection rules, so publishing any release
   sends a package straight to PyPI with no human gate. Publishing a test
   release from a branch whose version is not yet on PyPI will publish that
   version for real.

After the release
-----------------

Merge the release branch into ``main``. In practice this happens a couple of
minutes after the release is published.

The push to ``main`` is a separate trigger and starts the routine automation:
the nightly Windows build, the Docker Hub images, the site database refresh and
the test suite.

Because the release branch is merged with a squash, the commit that lands on
``main`` is not the commit the tag points at. This means ``vX.Y.Z`` is not an
ancestor of ``main``. It is expected, and it is why a packager should build from
the tag rather than looking for it in the branch history.

Tags in this repository
-----------------------

**Release tags**, ``vX.Y.Z``. Immutable, one per release, pointing at the tip of
a release branch. These are the only tags a packager should build from.

**Nightly tags**, ``nightly-main`` and ``nightly-dev``. Moving tags. Every push
to the matching branch rebuilds the Windows binary and force-updates the tag to
the built commit, so the tag always matches the attached ``.exe``. The releases
behind them are marked as prereleases so they never take the "latest" marker
from a real release. Never pin anything to these: the ref is stable but its
content is not.

**Legacy tags**, ``main``, ``dev``, ``test`` and ``dev-564`` through
``dev-571``. Left over from an earlier version of the Windows build, which used
the branch name directly as the tag name. Nothing creates or updates them any
more. Two of them still carry GitHub releases with a Windows binary attached,
built in April 2026, so anything downloaded from them is old.

.. warning::
   A tag named ``main`` shadows the branch of the same name. ``git rev-parse
   main`` warns that the refname is ambiguous and answers with the tag, so
   ``git show main:some/file`` reads from the tag's commit and not from the
   branch head. Tools that resolve a bare ref hit this too: a remote build that
   is told to build ``main`` may build the tag. Use ``refs/heads/main``
   explicitly, or clone with ``--no-tags``. The site data workflow works around
   it with a ``git tag -d main`` step before it touches any ref.

Where the artifacts end up
--------------------------

Published automatically on release:

- **PyPI**, the source distribution and the wheel.
- **GitHub release assets**, the Windows ``maigret_standalone.exe``.

Published automatically on every push to ``main``:

- **Docker Hub**, the CLI and web images.

Published by hand:

- **Snap**, built with ``snapcraft`` and uploaded to the ``latest/stable``
  channel for amd64 and arm64. Uploading a revision does not touch the store
  listing: the summary, the description and the icon change only when
  ``snapcraft upload-metadata <snap-file>`` is run, so run it whenever those
  fields change in ``snap/snapcraft.yaml``, or the store keeps serving the old
  text.

Maintained downstream, outside this repository:

- The AUR, Homebrew core, MacPorts and nixpkgs normally follow a new release
  within a day or two without being asked.
- BlackArch is updated through a pull request to the BlackArch repository.

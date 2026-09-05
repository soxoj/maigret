.. _release-process:

Release process
===============

This page describes how a Maigret release is cut, what each git tag in the
repository means, and which automation reacts to what. It is written for
maintainers and for downstream packagers who need to know which ref to build
from.

Where the version lives
-----------------------

The version is stored in two files and both have to be changed together:

- ``pyproject.toml``, the ``version`` field under ``[tool.poetry]``
- ``maigret/__version__.py``, the ``__version__`` string

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
- ``pyinstaller.yml`` builds ``maigret_standalone.exe`` under Wine and attaches
  it to the release. The binary appears a few minutes after the release itself,
  because PyInstaller is slow under Wine.

Both check out ``refs/tags/vX.Y.Z``, so both build the released code rather than
the current head of a branch.

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

# Extra sites (maigretexpanded)

This fork includes `sites_extra.json` (root) and example checker(s) in `maigret/sites/`.

Usage notes:
- You can point Maigret at `sites_extra.json` by setting the environment variable:
  export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"

- If Maigret loads sites from a single file by default, merge or adapt the loader so extra sites are merged at runtime.
- The example checker is a minimal module; integrate it into Maigret's site registry if you want it to run automatically.

Tests:
- Create a virtualenv and install dev deps:
  python -m venv .venv
  source .venv/bin/activate
  pip install pytest responses requests

- Run tests:
  pytest -q


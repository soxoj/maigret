# Opt-in extra checkers (maigretexpanded)

This fork supports *optional* additional site checkers (API-backed or extra scraping) kept separate from upstream Maigret.

## Enabling extras locally

1. Put extra-site definitions in `sites_extra.json` (root). Each key is an extra site id. The loader will read this file when `MAIGRET_EXTRA_SITES` points to it.

2. Example: enable extras at runtime:
```bash
export MAIGRET_EXTRA_SITES="$(pwd)/sites_extra.json"


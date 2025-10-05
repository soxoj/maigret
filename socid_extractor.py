# socid_extractor.py — temporary shim for local development/tests
# This forwards to maigret_sites_example.socid_extractor when available.
#
# TODO: replace this shim with the real 'socid_extractor' package before upstreaming.

try:
    # prefer the local dev stub if available
    from maigret_sites_example.socid_extractor import extract, parse  # type: ignore
except Exception:
    # fallback implementations: minimal, safe, and deterministic
    def extract(text):
        # return empty list if nothing to extract
        return []

    def parse(text):
        # return an empty dict / parsed object placeholder
        return {}
__all__ = ["extract", "parse"]

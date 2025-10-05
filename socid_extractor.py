# socid_extractor.py — temporary shim for local development/tests
# This forwards to maigret_sites_example.socid_extractor.extract so
# `import socid_extractor` keeps working while we iterate.
#
# TODO: replace this shim with the real 'socid_extractor' package before upstreaming.

try:
    # prefer the local dev stub if available
    from maigret_sites_example.socid_extractor import extract  # type: ignore
except Exception:
    # fallback: provide a safe no-op extract function
    def extract(text):
        return []
__all__ = ["extract"]

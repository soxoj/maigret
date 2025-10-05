"""
Local shim for socid_extractor used for tests / local development.
Create a proper dependency or replace this with the real package before upstreaming.
"""
def extract(text):
    # Return an empty list or minimal structure Maigret expects.
    # Adjust this shape if Maigret expects different return values.
    return []

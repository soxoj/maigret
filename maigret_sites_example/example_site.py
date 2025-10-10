"""
Lightweight example checker module.

This is intentionally defensive:
 - If Maigret's BaseChecker is importable, we subclass it.
 - Otherwise the module still exposes a callable `check(nickname, user_agent=None)` function
   so you can wire it into Maigret's registry manually if needed.

Adapt registration to Maigret internals (register this checker in their site registry).
"""
import requests

try:
    from maigret.checker import BaseChecker  # best-effort import; adapt if path differs
    _HAS_BASE = True
except Exception:
    BaseChecker = object
    _HAS_BASE = False

class ExampleSiteChecker(BaseChecker):
    site_name = "example_site"

    def __init__(self, user_agent=None):
        self.user_agent = user_agent or "maigret/extended (+https://github.com/dmoney96/maigretexpanded)"

    def check(self, nickname):
        url = f"https://www.example.com/{nickname}"
        headers = {"User-Agent": self.user_agent}
        try:
            r = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            return {"status": "error", "error": str(e)}

        if r.status_code == 404:
            return {"status": "not_found"}

        # JSON endpoint example
        if "application/json" in r.headers.get("Content-Type", ""):
            try:
                data = r.json()
                if data.get("profile") or data.get("exists"):
                    return {"status": "found", "url": url}
                return {"status": "not_found"}
            except Exception:
                pass

        # HTML heuristics
        text = r.text.lower()
        if "class=\"profile-header\"" in r.text or "data-user-id" in r.text or "profile not found" not in text:
            # basic positive heuristic (refine for real sites)
            return {"status": "found", "url": url}

        return {"status": "unknown"}

# convenience function for non-class consumers
def check(nickname, user_agent=None):
    c = ExampleSiteChecker(user_agent=user_agent)
    return c.check(nickname)

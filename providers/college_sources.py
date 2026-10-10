from datetime import datetime, timezone
from .base import Provider, ProviderError, get_json

class HipoUniversities(Provider):
    name = "Hipo Universities API"; category = "Colleges (institution directory)"; needs_auth = False
    coverage = "Name, country, state, website only. No courses, recruiters or placement statistics."
    docs = "https://github.com/Hipo/university-domains-list"
    def search(self, query, limit=50, country="India"):
        d = get_json("http://universities.hipolabs.com/search", params={"name": query, "country": country})
        if not isinstance(d, list): raise ProviderError("Unexpected response shape")
        return [normalize_hipo(x) for x in d[:limit]]

def normalize_hipo(x):
    web = (x.get("web_pages") or [None])[0]
    return {"college_name": x.get("name"), "website": web, "state": x.get("state-province"), "country": x.get("country"),
            "source_name": "Hipo Universities API", "source_url": web or "https://github.com/Hipo/university-domains-list",
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

class PlacementReports(Provider):
    name = "Placement reports (college sites / NIRF)"; category = "Placement"; needs_auth = False
    coverage = "No structured API verified; placement figures are not auto-collected."
    def configured(self): return False
    def search(self, query, limit=25): raise ProviderError("Not connected. Placement stats are never guessed.")

COLLEGE_PROVIDERS = [HipoUniversities(), PlacementReports()]

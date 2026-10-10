import re
from datetime import datetime, timezone
import config
from .base import Provider, ProviderError, get_json

def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _k(s): return re.sub(r"[^a-z0-9]", "", str(s).lower())
def pick(rec, *names):
    """Tolerant field lookup (case/underscore-insensitive) because OGD field names are not verified offline."""
    idx = {_k(k): v for k, v in rec.items()}
    for n in names:
        v = idx.get(_k(n))
        if v not in (None, "", "NA", "N/A"): return v
    return None

MCA_URL = "https://api.data.gov.in/resource/4dbe5667-7b6b-41d7-82af-211562424d9a"

class DataGovInMCA(Provider):
    name = "data.gov.in - MCA Company Master Data"; category = "Companies (India, all RoC-registered)"; needs_auth = True
    coverage = ("Official Indian company registry (millions of companies). It is NOT a startup list: no funding, investors, hiring or DPIIT-recognised flag. "
                "Search = exact name filter, then a limited paged scan (MCA_MAX_SCAN_PAGES) with substring match, so broad names may miss records.")
    docs = "https://www.data.gov.in/catalog/company-master-data"
    def configured(self): return bool(config.DATA_GOV_IN_API_KEY)
    def _page(self, offset, limit, filters=None):
        p = {"api-key": config.DATA_GOV_IN_API_KEY, "format": "json", "offset": offset, "limit": limit}
        for k, v in (filters or {}).items(): p[f"filters[{k}]"] = v
        d = get_json(MCA_URL, params=p)
        if not isinstance(d, dict) or "records" not in d: raise ProviderError(f"Unexpected response: {str(d)[:200]}")
        return d["records"]
    def search(self, query, limit=50):
        if not self.configured(): raise ProviderError("DATA_GOV_IN_API_KEY not set.")
        recs = []
        try: recs = self._page(0, limit, {"company_name": query.upper()})  # exact-name filter (field name per OGD; verify on first run)
        except ProviderError: recs = []
        if not recs:
            q = query.lower()
            for pg in range(config.MCA_MAX_SCAN_PAGES):
                rows = self._page(pg * 500, 500)
                if not rows: break
                recs += [r for r in rows if q in str(pick(r, "company_name", "name") or "").lower()]
                if len(recs) >= limit: break
        out = [normalize_mca(r) for r in recs[:limit]]
        if recs and not any(o["company_name"] for o in out):
            raise ProviderError(f"Records returned but known name field missing; fields seen: {list(recs[0])[:12]}")
        return out

def normalize_mca(r):
    cin = pick(r, "cin", "corporate_identification_number")
    reg = str(pick(r, "date_of_registration", "company_registration_date") or "")
    yr = re.search(r"(19|20)\d{2}", reg)
    status = pick(r, "company_status"); cls = pick(r, "company_class"); biz = pick(r, "principal_business_activity_as_per_cin", "principal_business_activity", "industrial_classification")
    cap = pick(r, "authorized_cap", "authorized_capital")
    desc = "; ".join(x for x in [f"Status: {status}" if status else "", f"Class: {cls}" if cls else "", f"Authorized capital INR: {cap}" if cap else "", f"Business: {biz}" if biz else ""] if x) or None
    return {"company_name": pick(r, "company_name", "name"), "description": desc, "industry": biz, "location": pick(r, "registered_state", "state", "company_state_code"),
            "country": "India", "founded_year": int(yr.group()) if yr else None, "source_name": "data.gov.in - MCA Company Master Data",
            "source_url": f"https://www.data.gov.in/catalog/company-master-data#{cin}" if cin else "https://www.data.gov.in/catalog/company-master-data", "retrieved_at": _now()}

class YouTubeInfluencers(Provider):
    name = "YouTube Data API v3"; category = "Influencers (India, YouTube channels)"; needs_auth = True
    coverage = "YouTube channels only (regionCode=IN). Instagram/X/LinkedIn have no public search API, so they are not covered. Free quota: ~100 searches/day."
    docs = "https://developers.google.com/youtube/v3/docs/search/list"
    def configured(self): return bool(config.YOUTUBE_API_KEY)
    def search(self, query, limit=25):
        if not self.configured(): raise ProviderError("YOUTUBE_API_KEY not set.")
        s = get_json("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "type": "channel", "q": query, "regionCode": "IN",
                     "maxResults": min(limit, 50), "key": config.YOUTUBE_API_KEY})
        ids = [i["id"]["channelId"] for i in s.get("items", []) if i.get("id", {}).get("channelId")]
        if not ids: return []
        c = get_json("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet,statistics", "id": ",".join(ids), "key": config.YOUTUBE_API_KEY})
        return [normalize_yt(i) for i in c.get("items", [])]

def normalize_yt(i):
    sn, st = i.get("snippet", {}), i.get("statistics", {})
    num = lambda v: int(v) if str(v).isdigit() else None
    return {"channel_name": sn.get("title"), "handle": sn.get("customUrl"), "description": (sn.get("description") or "")[:300] or None, "country": sn.get("country"),
            "subscribers": None if st.get("hiddenSubscriberCount") else num(st.get("subscriberCount")), "total_views": num(st.get("viewCount")),
            "video_count": num(st.get("videoCount")), "channel_created": (sn.get("publishedAt") or "")[:10] or None,
            "source_name": "YouTube Data API v3", "source_url": f"https://www.youtube.com/channel/{i.get('id')}", "retrieved_at": _now()}

class InstagramInfluencers(Provider):
    """PLACEHOLDER: Instagram/X/LinkedIn have no public influencer-search API. Implement here if you get authorized access."""
    name = "Instagram / other platforms - placeholder"; category = "Influencers"; needs_auth = True
    coverage = "Not connected. Use CSV import in Influencer Explorer."
    def configured(self): return False
    def search(self, query, limit=25): raise ProviderError("Placeholder: no public API. Import a CSV instead.")

INDIA_STARTUP = [DataGovInMCA()]
INFLUENCER_PROVIDERS = [YouTubeInfluencers(), InstagramInfluencers()]

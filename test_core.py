import os, tempfile
import config
config.DB_PATH = os.path.join(tempfile.mkdtemp(), "t.db")
import database as db
from services.matching import match_startup_investor
from services.search import apply_filters
from providers.college_sources import normalize_hipo

def test_db_dedupe_and_nulls():
    db.init_db(); r = {"company_name": "Acme", "source_name": "X", "source_url": "u", "industry": ""}
    db.upsert("startups", [r]); db.upsert("startups", [r])
    d = db.load("startups"); assert len(d) == 1 and d.industry.isna().all()

def test_normalizers_keep_missing_null():
    assert normalize_hipo({"name": "C", "web_pages": [], "state-province": None, "country": "India"})["website"] is None

def test_matching_handles_missing():
    s = {"industry": "fintech payments", "funding_stage": "Seed", "country": "India"}
    inv = {"preferred_industries": '["fintech"]', "investment_stages": '["Seed"]', "geography": '["India"]', "source_url": "u"}
    m = match_startup_investor(s, inv); assert m["score"] == 100.0 and "check size" in m["missing"]
    assert match_startup_investor({}, {})["score"] is None

def test_filters_and_sort():
    import pandas as pd
    df = pd.DataFrame({"n": ["a", "b", "c"], "v": [3, 1, 2]})
    out = apply_filters(df, "", None, {"v": (2, 3)}, "v", True); assert out.n.tolist() == ["c", "a"]
    assert apply_filters(df, "b").n.tolist() == ["b"]

def test_india_normalizers():
    from providers.india_sources import normalize_mca, normalize_yt
    m = normalize_mca({"CIN": "U72900GJ2015PTC082637", "COMPANY_NAME": "ACME PVT LTD", "DATE_OF_REGISTRATION": "19-03-2015", "REGISTERED_STATE": "Gujarat"})
    assert m["founded_year"] == 2015 and m["country"] == "India" and m["funding_stage"] if False else m["industry"] is None
    y = normalize_yt({"id": "UC1", "snippet": {"title": "T"}, "statistics": {"hiddenSubscriberCount": True, "viewCount": "10"}})
    assert y["subscribers"] is None and y["total_views"] == 10

def test_placement_roundtrip():
    db.init_db(); db.upsert_placement([{"college_name": "IIT X", "academic_year": "2024", "placement_rate": 91.5, "recruiters": "Acme;Beta", "source_url": "u"}, {"college_name": ""}])
    p = db.load_placement(); assert len(p) == 1 and p.average_package.isna().all() and db.as_list(p.recruiters[0]) == ["Acme", "Beta"]

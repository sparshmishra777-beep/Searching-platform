import re
from config import MATCH_WEIGHTS
from database import as_list

def _tok(s): return {t for t in re.findall(r"[a-z]{3,}", (s or "").lower())}
def _blank(v): return v is None or (isinstance(v, float) and v != v) or v == ""

def match_startup_investor(s, inv, w=MATCH_WEIGHTS):
    """Rule-based compatibility estimate. Only factors with data on both sides count; unknowns are reported, never assumed."""
    ev, miss, got = [], [], {}
    inds = _tok(" ".join(as_list(inv.get("preferred_industries")) + [str(inv.get("investment_focus") or "")]))
    if _blank(s.get("industry")) or not inds: miss.append("industry")
    else:
        ov = _tok(s["industry"]) & inds; got["industry"] = 1.0 if ov else 0.0
        ev.append(f"Industry terms {'overlap: ' + ', '.join(sorted(ov)) if ov else 'do not overlap'}")
    stages = [x.lower() for x in as_list(inv.get("investment_stages"))]
    if _blank(s.get("funding_stage")) or not stages: miss.append("funding stage")
    else:
        got["stage"] = 1.0 if s["funding_stage"].lower() in stages else 0.0
        ev.append(f"Stage '{s['funding_stage']}' {'is' if got['stage'] else 'is not'} in investor stages")
    geo = [x.lower() for x in as_list(inv.get("geography"))]
    loc = " ".join(str(s.get(k) or "") for k in ("country", "location")).lower()
    if not loc.strip() or not geo: miss.append("geography")
    else:
        got["geography"] = 1.0 if any(g in loc for g in geo) else 0.0
        ev.append(f"Geography {'matches' if got['geography'] else 'does not match'} ({', '.join(geo)})")
    amt, lo, hi = s.get("funding_amount"), inv.get("min_check"), inv.get("max_check")
    if _blank(amt) or (_blank(lo) and _blank(hi)): miss.append("check size")
    else:
        ok = (_blank(lo) or amt >= lo) and (_blank(hi) or amt <= hi); got["check"] = 1.0 if ok else 0.0
        ev.append(f"Funding amount {amt:,.0f} {'within' if ok else 'outside'} check range")
    a = _tok(s.get("description")); b = _tok(" ".join(as_list(inv.get("portfolio_companies"))) + " " + str(inv.get("investment_focus") or ""))
    if not a or not b: miss.append("description/portfolio similarity")
    else:
        got["similarity"] = len(a & b) / len(a | b); ev.append(f"Text similarity {got['similarity']:.0%}")
    tot = sum(w[k] for k in got)
    score = round(100 * sum(w[k] * v for k, v in got.items()) / tot, 1) if tot else None
    return {"score": score, "criteria_used": list(got), "evidence": ev, "missing": miss,
            "coverage": round(tot / sum(w.values()) * 100), "source_url": inv.get("source_url")}

def match_company_college(s, col):
    got, ev, miss = {}, [], []
    courses = _tok(" ".join(as_list(col.get("courses"))))
    if _blank(s.get("industry")) or not courses: miss.append("industry vs courses")
    else:
        ov = _tok(s["industry"]) & courses; got["industry"] = 1.0 if ov else 0.0; ev.append(f"Industry/course overlap: {sorted(ov) or 'none'}")
    if _blank(s.get("location")) or _blank(col.get("state")): miss.append("location")
    else:
        got["location"] = 1.0 if str(col["state"]).lower() in str(s["location"]).lower() else 0.0; ev.append(f"State {'matches' if got['location'] else 'differs'}")
    rec = [r.lower() for r in as_list(col.get("recruiters"))]
    if not rec: miss.append("recruiter history")
    else:
        got["recruiter"] = 1.0 if str(s.get("company_name", "")).lower() in rec else 0.0
        ev.append("Company listed among recruiters" if got["recruiter"] else "Company not in recorded recruiters")
    score = round(100 * sum(got.values()) / len(got), 1) if got else None
    return {"score": score, "criteria_used": list(got), "evidence": ev, "missing": miss, "source_url": col.get("source_url")}

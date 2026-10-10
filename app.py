import pandas as pd, plotly.express as px, streamlit as st
import database as db
from providers.startup_sources import STARTUP_PROVIDERS
from providers.investor_sources import INVESTOR_PROVIDERS
from providers.college_sources import COLLEGE_PROVIDERS
from providers.india_sources import INDIA_STARTUP, INFLUENCER_PROVIDERS
from providers.base import ProviderError
from services.search import apply_filters
from services.matching import match_startup_investor, match_company_college

st.set_page_config(page_title="Startup, Investor & College Intelligence", layout="wide")
db.init_db()
STARTUP_PROVIDERS = INDIA_STARTUP + STARTUP_PROVIDERS
ALL = STARTUP_PROVIDERS + INFLUENCER_PROVIDERS + INVESTOR_PROVIDERS + COLLEGE_PROVIDERS
TABLE_PROVIDERS = {"startups": STARTUP_PROVIDERS, "investors": INVESTOR_PROVIDERS, "colleges": COLLEGE_PROVIDERS, "influencers": INFLUENCER_PROVIDERS}

REQ = {"startups": "company_name", "investors": "investor_name", "colleges": "college_name", "influencers": "channel_name"}

def run_live(table, provider, query):
    try:
        recs = provider.search(query)
        n = db.upsert(table, recs); db.log(provider.name, provider.category, query, "ok", n)
        return pd.DataFrame(recs), None
    except ProviderError as e:
        db.log(provider.name, provider.category, query, "error", 0, str(e)); return None, str(e)
    except Exception as e:  # malformed data etc.
        db.log(provider.name, provider.category, query, "error", 0, repr(e)); return None, repr(e)

def csv_import(key, cols, required, saver):
    with st.expander("Import your own CSV (use this where no API exists)"):
        tcols = [c for c in cols if c != "retrieved_at"]
        st.download_button("Download blank CSV template", ",".join(tcols) + "\n", f"{key}_template.csv", "text/csv", key=key + "dl")
        st.caption("List fields (e.g. investment_stages, recruiters): separate values with semicolons. Import only data you are allowed to use; keep source_name / source_url accurate. Blank cells stay 'Not available'.")
        up = st.file_uploader("CSV file", type="csv", key=key + "up")
        if up and st.button("Import", key=key + "imp"):
            try: d = pd.read_csv(up)
            except Exception as e: st.error(f"Could not read CSV: {e}"); return
            if required not in d.columns: st.error(f"Missing required column: {required}"); return
            if "source_name" not in d: d["source_name"] = "User CSV import"
            d = d[[c for c in tcols if c in d.columns]]
            n = saver(d.astype(object).where(d.notna(), None).to_dict("records"))
            db.log("CSV import", key, up.name, "ok", n); st.success(f"Imported {n} records")

def explorer(table, title, text_cols, multi_cols, range_cols):
    st.header(title)
    provs = TABLE_PROVIDERS[table]
    csv_import(table, db.SCHEMAS[table], REQ[table], lambda r: db.upsert(table, r))
    mode = st.radio("Mode", ["Live search", "Saved data (SQLite)"], horizontal=True, key=table + "m")
    ss = st.session_state; live_df = ss.get(table + "live")
    if mode == "Live search":
        with st.form(table + "form"):
            c1, c2, c3 = st.columns([2, 2, 1])
            p = c1.selectbox("Source", provs, format_func=lambda x: x.name)
            q = c2.text_input("Search (fetches from the source every time)")
            go = c3.form_submit_button("Fetch live")
            st.caption(f"Coverage: {p.coverage}")
        if go and q:
            with st.spinner("Contacting source..."):
                df_, err = run_live(table, p, q)
            if err: st.error(f"{p.name} failed: {err}"); ss.pop(table + "live", None); live_df = None
            elif df_.empty: st.warning("Source returned no results."); ss.pop(table + "live", None); live_df = None
            else: ss[table + "live"] = live_df = df_; ss[table + "ts"] = db.now(); ss[table + "src"] = p.name
        if live_df is not None: st.success(f"LIVE results from {ss[table + 'src']}, retrieved {ss[table + 'ts']} UTC (also saved to SQLite).")
        else: st.info("Search above to fetch live. Saved records below are NOT live.")
    else: live_df = None
    saved = db.load(table)
    df = live_df if live_df is not None and not live_df.empty else saved
    label = "LIVE" if df is live_df else "SAVED (may be stale)"
    if df.empty: st.info("No records yet. Use Live search" + (" or import a CSV." if table == "investors" else ".")); return
    st.subheader(f"{len(df)} records — {label}")
    if "retrieved_at" in df and df["retrieved_at"].notna().any(): st.caption(f"Last fetched: {df['retrieved_at'].max()} UTC")
    with st.expander("Filters & sorting", expanded=True):
        kw = st.text_input("Keyword (any column)", key=table + "kw")
        multi = {c: st.multiselect(c, sorted(df[c].dropna().astype(str).unique()), key=table + c) for c in multi_cols if c in df and df[c].notna().any()}
        ranges = {}
        for c in range_cols:
            s = pd.to_numeric(df.get(c), errors="coerce").dropna() if c in df else []
            if len(s) and s.min() < s.max():
                lo, hi = st.slider(c, float(s.min()), float(s.max()), (float(s.min()), float(s.max())), key=table + c); ranges[c] = (lo, hi)
        c1, c2, c3 = st.columns(3)
        sort_by = c1.selectbox("Sort by", [None] + [c for c in df.columns if c != "id"], key=table + "s")
        asc = c2.radio("Order", ["Ascending", "Descending"], horizontal=True, key=table + "o") == "Ascending"
        limit = c3.number_input("Max rows", 10, 1000, 100, key=table + "l")
    out = apply_filters(df.astype({c: str for c in multi}), kw, multi, ranges, sort_by, asc, int(limit)) if multi else apply_filters(df, kw, None, ranges, sort_by, asc, int(limit))
    st.dataframe(out.fillna("Not available"), use_container_width=True, hide_index=True,
                 column_config={"source_url": st.column_config.LinkColumn("source_url"), "website": st.column_config.LinkColumn("website")})
    st.download_button("Export CSV", out.to_csv(index=False).encode(), f"{table}.csv", "text/csv")
    return out

page = st.sidebar.radio("Navigate", ["Dashboard", "Global Search", "Startup Explorer", "Influencer Explorer", "Investor Explorer", "College Explorer", "Placement Intelligence", "Matching", "Data Sources"])

if page == "Dashboard":
    st.header("Dashboard")
    S, I, C = db.load("startups"), db.load("investors"), db.load("colleges")
    with db.conn() as c: P = c.execute("SELECT COUNT(*) FROM placement_records").fetchone()[0]
    cols = st.columns(4); [col.metric(n, v) for col, n, v in zip(cols, ["Startups", "Investors", "Colleges", "Placement records"], [len(S), len(I), len(C), P])]
    lg = db.logs()
    st.caption(f"Most recent refresh: {lg[lg.status=='ok'].at.max() if (lg.status=='ok').any() else 'never'} | Errors logged: {(lg.status=='error').sum()}")
    st.write("Connected & configured sources:", ", ".join(p.name for p in ALL if p.configured()) or "none")
    for df, col, t in [(S, "industry", "Startups by industry"), (S, "country", "Startups by country"), (C, "state", "Colleges by state")]:
        if not df.empty and df[col].notna().any():
            v = df[col].value_counts().reset_index(); st.plotly_chart(px.bar(v, x=col, y="count", title=t), use_container_width=True)
    PL = db.load_placement()
    if PL.empty: st.info("No placement records imported yet; placement charts are not shown (no fabricated values).")
    else:
        for col, t in [("placement_rate", "Average placement rate by college"), ("average_package", "Average package by college")]:
            g = pd.to_numeric(PL[col], errors="coerce").groupby(PL.college_name).mean().dropna().reset_index()
            if len(g): st.plotly_chart(px.bar(g, x="college_name", y=col, title=t), use_container_width=True)

elif page == "Startup Explorer":
    explorer("startups", "Startup Explorer", ["company_name"], ["industry", "country", "location", "funding_stage", "hiring_status"], ["funding_amount", "founded_year"])
elif page == "Influencer Explorer":
    explorer("influencers", "Influencer Explorer (India, YouTube)", ["channel_name"], ["country"], ["subscribers", "total_views", "video_count"])
elif page == "Global Search":
    st.header("Global Search (live, every time)")
    with st.form("gs"):
        q = st.text_input("Search all configured sources at once"); go = st.form_submit_button("Fetch live from all")
    if go and q:
        for table, provs in TABLE_PROVIDERS.items():
            for p in provs:
                if not p.configured(): st.caption(f"- {p.name}: skipped (not configured / not connected)"); continue
                with st.spinner(p.name):
                    d_, err = run_live(table, p, q)
                if err: st.error(f"{p.name}: {err}")
                else:
                    st.subheader(f"{p.name} - {len(d_)} LIVE results ({db.now()} UTC)")
                    if len(d_): st.dataframe(d_.fillna("Not available"), use_container_width=True, hide_index=True, column_config={"source_url": st.column_config.LinkColumn("source_url")})
elif page == "Investor Explorer":
    explorer("investors", "Investor Explorer", ["investor_name"], ["investor_type", "organization"], ["min_check", "max_check"])
elif page == "College Explorer":
    explorer("colleges", "College Explorer", ["college_name"], ["state", "city", "university"], ["placement_rate", "average_package"])
elif page == "Placement Intelligence":
    st.header("Placement Intelligence")
    st.info("No structured placement API exists, so none is connected and nothing is estimated. Import placement data you collected from NIRF / official college placement reports via CSV.")
    csv_import("placement", db.PLACEMENT_COLS, "college_name", db.upsert_placement)
    PL = db.load_placement()
    if PL.empty: st.stop()
    PL["academic_year"] = PL["academic_year"].map(lambda v: None if pd.isna(v) else str(v))
    st.caption(f"{len(PL)} placement records. Last imported: {PL['retrieved_at'].max()} UTC (saved data, not live).")
    kw = st.text_input("Keyword", key="plkw")
    multi = {c: st.multiselect(c, sorted(PL[c].dropna().unique()), key="pl" + c) for c in ["college_name", "academic_year"]}
    ranges = {}
    for c in ["placement_rate", "average_package", "highest_package"]:
        s_ = pd.to_numeric(PL[c], errors="coerce").dropna()
        if len(s_) and s_.min() < s_.max(): ranges[c] = st.slider(c, float(s_.min()), float(s_.max()), (float(s_.min()), float(s_.max())), key="pl" + c)
    c1, c2 = st.columns(2)
    sb = c1.selectbox("Sort by", [None] + list(PL.columns), key="plsort"); asc = c2.radio("Order", ["Ascending", "Descending"], horizontal=True, key="plord") == "Ascending"
    out = apply_filters(PL, kw, multi, ranges, sb, asc, 500)
    st.dataframe(out.fillna("Not available"), use_container_width=True, hide_index=True, column_config={"source_url": st.column_config.LinkColumn("source_url")})
    st.download_button("Export CSV", out.to_csv(index=False).encode(), "placements.csv", "text/csv")
    rc = pd.Series([r for v in out["recruiters"] for r in db.as_list(v)]).value_counts().head(15).reset_index()
    if len(rc): rc.columns = ["recruiter", "records"]; st.plotly_chart(px.bar(rc, x="recruiter", y="records", title="Top recruiters in filtered records"), use_container_width=True)
elif page == "Matching":
    st.header("Matching Engine"); st.caption("Scores are algorithmic compatibility estimates, not probabilities of investment or hiring.")
    S, I, C = db.load("startups"), db.load("investors"), db.load("colleges")
    PL = db.load_placement()
    if not PL.empty:  # fold imported placement recruiters into colleges; add colleges known only from placement data
        rec = {}
        for _, r in PL.iterrows(): rec.setdefault(db.norm_name(r.college_name), [r.college_name, set()])[1].update(db.as_list(r.recruiters))
        known = set(C.college_name.map(db.norm_name)) if len(C) else set()
        C = pd.concat([C, pd.DataFrame([{"college_name": v[0], "source_url": None} for k, v in rec.items() if k not in known])], ignore_index=True)
        C["recruiters"] = [sorted(set(db.as_list(x.recruiters)) | rec.get(db.norm_name(x.college_name), ["", set()])[1]) for x in C.itertuples()]
    if S.empty: st.info("Add startups first (live search or CSV import).")
    else:
        name = st.selectbox("Startup / company", S.company_name.tolist()); s = S[S.company_name == name].iloc[0].to_dict()
        t1, t2 = st.tabs(["Startup → Investor", "Company → College"])
        with t1:
            rows = []
            for _, r in I.iterrows():
                m = match_startup_investor(s, r.to_dict())
                if m["score"] is not None: rows.append({"investor": r.investor_name, "score": m["score"], "data coverage %": m["coverage"], "evidence": "; ".join(m["evidence"]), "missing": ", ".join(m["missing"]) or "—", "source": m["source_url"]})
            if rows: st.dataframe(pd.DataFrame(rows).sort_values("score", ascending=False), use_container_width=True, hide_index=True, column_config={"source": st.column_config.LinkColumn("source")})
            else: st.info("No investor has enough overlapping data (need e.g. industries, stages, geography). Import investors with those fields.")
        with t2:
            rows = []
            for _, r in C.iterrows():
                m = match_company_college(s, r.to_dict())
                if m["score"] is not None: rows.append({"college": r.college_name, "score": m["score"], "evidence": "; ".join(m["evidence"]), "missing": ", ".join(m["missing"]), "source": m["source_url"]})
            if rows: st.dataframe(pd.DataFrame(rows).sort_values("score", ascending=False), use_container_width=True, hide_index=True)
            else: st.info("Retrieved colleges lack courses/recruiters/location data needed to match.")
elif page == "Data Sources":
    st.header("Data Sources"); lg = db.logs()
    rows = []
    for p in ALL:
        l = lg[lg.provider == p.name]; ok = l[l.status == "ok"]; er = l[l.status == "error"]
        rows.append({"Provider": p.name, "Category": p.category, "Auth required": "Yes" if p.needs_auth else "No",
                     "Status": "Configured" if p.configured() else "Not connected / missing credentials",
                     "Last success": ok.at.max() if len(ok) else "never", "Records retrieved": int(ok.records.sum()) if len(ok) else 0,
                     "Last error": er.iloc[0].error if len(er) else "", "Coverage": p.coverage})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader("Ingestion log"); st.dataframe(lg, use_container_width=True, hide_index=True)

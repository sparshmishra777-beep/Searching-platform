import sqlite3, json, hashlib, re
from datetime import datetime, timezone
import pandas as pd
import config

SCHEMAS = {
 "startups": ["company_name","website","description","industry","location","country","founded_year","funding_stage",
              "funding_amount","investors","employee_count","hiring_status","source_name","source_url","retrieved_at"],
 "investors": ["investor_name","organization","investor_type","website","investment_focus","preferred_industries",
               "investment_stages","geography","min_check","max_check","portfolio_companies","source_name","source_url","retrieved_at"],
 "influencers": ["channel_name","handle","description","country","subscribers","total_views","video_count","channel_created","website","source_name","source_url","retrieved_at"],
 "colleges": ["college_name","university","city","state","country","website","placement_cell_website","placement_officer",
              "courses","recruiters","placement_rate","average_package","highest_package","academic_year","source_name","source_url","retrieved_at"],
}
NUMERIC = {"subscribers","total_views","video_count","founded_year","funding_amount","employee_count","min_check","max_check","placement_rate","average_package","highest_package"}

NAME_COL = {"startups":"company_name","investors":"investor_name","colleges":"college_name","influencers":"channel_name"}
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def conn():
    c = sqlite3.connect(config.DB_PATH); c.row_factory = sqlite3.Row; return c

def init_db():
    with conn() as c:
        for t, cols in SCHEMAS.items():
            defs = ", ".join(f"{k} {'REAL' if k in NUMERIC else 'TEXT'}" for k in cols)
            c.execute(f"CREATE TABLE IF NOT EXISTS {t} (id TEXT PRIMARY KEY, norm_name TEXT, {defs})")
        c.execute("""CREATE TABLE IF NOT EXISTS placement_records (id TEXT PRIMARY KEY, college_id TEXT, college_name TEXT, academic_year TEXT,
                     placement_rate REAL, average_package REAL, highest_package REAL, recruiters TEXT, source_name TEXT, source_url TEXT, retrieved_at TEXT)""")
        c.execute("CREATE TABLE IF NOT EXISTS ingestion_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, category TEXT, query TEXT, status TEXT, records INTEGER, error TEXT, at TEXT)")

def norm_name(s): return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def make_id(table, rec):
    name = NAME_COL[table]
    key = f"{rec.get('source_name')}|{rec.get('source_url') or norm_name(rec.get(name))}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]

def upsert(table, records):
    cols = SCHEMAS[table]; n = 0
    with conn() as c:
        for r in records:
            r = {k: (None if v in ("", [], None) or (isinstance(v, float) and v != v) else v) for k, v in r.items()}
            row = {k: (json.dumps(r.get(k)) if isinstance(r.get(k), list) else r.get(k)) for k in cols}
            row["retrieved_at"] = row["retrieved_at"] or now()
            nm = NAME_COL[table]
            vals = [make_id(table, r), norm_name(r.get(nm))] + [row[k] for k in cols]
            c.execute(f"INSERT OR REPLACE INTO {table} (id,norm_name,{','.join(cols)}) VALUES ({','.join('?'*(len(cols)+2))})", vals); n += 1
    return n

def load(table):
    with conn() as c:
        df = pd.read_sql_query(f"SELECT * FROM {table}", c)
    return df.drop(columns=["norm_name"], errors="ignore")

def log(provider, category, query, status, records=0, error=None):
    with conn() as c:
        c.execute("INSERT INTO ingestion_logs (provider,category,query,status,records,error,at) VALUES (?,?,?,?,?,?,?)",
                  (provider, category, query, status, records, error, now()))

def logs(): 
    with conn() as c: return pd.read_sql_query("SELECT * FROM ingestion_logs ORDER BY id DESC", c)

def as_list(v):
    if v is None or (isinstance(v, float) and v != v): return []
    if isinstance(v, list): return v
    try:
        x = json.loads(v); return x if isinstance(x, list) else [str(x)]
    except Exception: return [s.strip() for s in re.split(r"[;,|]", str(v)) if s.strip()]

PLACEMENT_COLS = ["college_name","academic_year","placement_rate","average_package","highest_package","recruiters","source_name","source_url","retrieved_at"]

def upsert_placement(records):
    n = 0
    with conn() as c:
        for r in records:
            r = {k: (None if v in ("", None) or (isinstance(v, float) and v != v) else v) for k, v in r.items()}
            if not r.get("college_name"): continue
            rec = json.dumps(r["recruiters"]) if isinstance(r.get("recruiters"), list) else r.get("recruiters")
            pid = hashlib.sha1(f"{norm_name(r['college_name'])}|{r.get('academic_year')}|{r.get('source_url')}".encode()).hexdigest()[:16]
            c.execute("INSERT OR REPLACE INTO placement_records (id,college_id,college_name,academic_year,placement_rate,average_package,highest_package,recruiters,source_name,source_url,retrieved_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (pid, norm_name(r["college_name"]), r["college_name"], r.get("academic_year"), r.get("placement_rate"), r.get("average_package"),
                       r.get("highest_package"), rec, r.get("source_name") or "User CSV import", r.get("source_url"), r.get("retrieved_at") or now())); n += 1
    return n

def load_placement():
    with conn() as c: return pd.read_sql_query("SELECT * FROM placement_records", c).drop(columns=["college_id"], errors="ignore")

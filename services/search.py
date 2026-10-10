import pandas as pd

def apply_filters(df, keyword="", multi=None, ranges=None, sort_by=None, ascending=True, limit=100):
    d = df.copy()
    if keyword:
        mask = d.astype(str).apply(lambda s: s.str.contains(keyword, case=False, na=False, regex=False)).any(axis=1)
        d = d[mask]
    for col, vals in (multi or {}).items():
        if vals: d = d[d[col].isin(vals)]
    for col, (lo, hi) in (ranges or {}).items():
        if lo is not None: d = d[pd.to_numeric(d[col], errors="coerce") >= lo]
        if hi is not None: d = d[pd.to_numeric(d[col], errors="coerce") <= hi]
    if sort_by: d = d.sort_values(sort_by, ascending=ascending, na_position="last")
    return d.head(limit)

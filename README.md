# Indian Startup, Investor, Influencer & College-Placement Intelligence (prototype)

India-only. No US/UK sources.

## Run on Windows (PowerShell)
```
cd startup_intelligence
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then edit .env
streamlit run app.py
```

## Data coverage (what is live API vs CSV import)
| Data | Live API | Key | If no API |
|---|---|---|---|
| Startups / companies (India) | data.gov.in MCA Company Master Data (all Indian registered companies, not only startups; no funding data) | `DATA_GOV_IN_API_KEY` (free, data.gov.in -> register -> API key) | CSV import; Startup India = placeholder |
| Influencers (India) | YouTube Data API v3 (channels, regionCode=IN) | `YOUTUBE_API_KEY` (free, Google Cloud -> enable YouTube Data API v3 -> API key) | CSV import; Instagram etc. = placeholder |
| Colleges | Hipo Universities API (India; name/state/website only) | none | CSV import |
| Placement data | none exists | - | CSV import on Placement Intelligence page (NIRF / official college reports) |
| Investors | none verified | - | CSV import (investment stages, geography, check size, portfolio...) |

Every explorer has "Download blank CSV template" + import. List columns use semicolons. Nothing is estimated; blanks show "Not available".

## Pages
Dashboard, Global Search (live from all configured APIs every time), Startup / Influencer / Investor / College explorers (Live search = fetch every time; Saved data = SQLite, labelled stale), Placement Intelligence, Matching (startup->investor, company->college), Data Sources.

## Limitations
- Live endpoints were not tested in the build sandbox (no internet). Unit tests cover DB, normalizers, filters, matching, placement. Check the Data Sources page after your first run.
- MCA API supports exact name filter; otherwise a limited paged scan (`MCA_MAX_SCAN_PAGES`).
- Matching is a rule-based estimate (not a probability) and only uses fields that exist on both sides.
- RapidFuzz fuzzy duplicate review is not implemented; dedupe is by source+URL / normalized name.

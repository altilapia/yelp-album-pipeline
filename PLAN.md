# Yelp Album Tracker — Build Plan

## Goal
A web app that takes a public Yelp album URL, scrapes all businesses (handling infinite scroll), and writes name/category/link/rating to a Google Sheet. Runs on a daily schedule.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Web App (FastAPI + simple HTML form)                   │
│  - POST /scrape  { yelp_url }                           │
│  - GET  /  → form + list of tracked albums              │
└───────────────┬─────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────┐
│  Scraper (Playwright) → Parser (BeautifulSoup) →        │
│  Sheets uploader (gspread + service account)            │
└───────────────┬─────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────┐
│  Scheduler (APScheduler) — daily runs of tracked albums │
└─────────────────────────────────────────────────────────┘
```

## Repo layout
```
yelp-album-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + routes
│   ├── scraper.py           # Playwright: URL → HTML
│   ├── parser.py            # HTML → list of dicts
│   ├── sheets.py            # dicts → Google Sheet
│   ├── scheduler.py         # APScheduler config
│   ├── storage.py           # tracked-albums persistence (SQLite or JSON)
│   ├── config.py            # loads .env
│   └── templates/
│       └── index.html
├── tests/
│   ├── test_parser.py
│   └── fixtures/
│       └── sample_album.html  # already in place
├── credentials/               # gitignored
│   └── service-account.json
├── .env                       # gitignored
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── PLAN.md
```

## Build order
1. **Parser** — `app/parser.py` extracts name, biz_url, category, rating, review_count, price, neighborhood from a Yelp album HTML file. Test against `tests/fixtures/sample_album.html`. Should return ~52 rows for the sample.
2. **Sheets uploader** — `app/sheets.py` takes a list of dicts and upserts to Google Sheet by `biz_url`. Adds `first_seen` and `last_seen` timestamp columns. Reads sheet ID + credentials path from `.env`.
3. **Scraper** — `app/scraper.py` uses Playwright to open a URL, scroll until no new entries load, return the rendered HTML. Start non-headless to avoid bot detection; add stealth tweaks if needed.
4. **Wire it together** — a single function `run_pipeline(url)` that calls scraper → parser → sheets.
5. **Web app** — `app/main.py` with a FastAPI form that takes a URL and triggers `run_pipeline` as a background task. Simple HTML template.
6. **Scheduler** — `app/scheduler.py` reads tracked URLs from `app/storage.py` and runs `run_pipeline` on each, daily at the time set in `.env`.
7. **README** — setup instructions covering Google Cloud setup, conda env, .env config, running locally.

## Reproducibility requirements
- All secrets/config in `.env`, never hardcoded
- `.env.example` committed so others know what to set
- `requirements.txt` pinned versions
- `README.md` with full setup walkthrough
- Service-account JSON in `credentials/` (gitignored), path configurable via env

## Yelp scraping notes
- Yelp uses infinite scroll on album pages — must scroll until no new content before parsing
- Yelp fingerprints headless browsers; expect occasional CAPTCHAs
- Start with `headless=False`, add realistic scroll delays
- Escalation path if blocked: playwright-stealth → residential proxy

## Out of scope (for now)
- Multi-tenant / multi-user support
- OAuth (sticking with service account)
- Deployment to a server (will run locally first)
- UI beyond a basic form
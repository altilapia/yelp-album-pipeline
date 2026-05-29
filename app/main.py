from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import storage
from app.config import GOOGLE_SHEET_ID
from app.database import init_db
from app.pipeline import run_pipeline
from app.scheduler import create_scheduler
from app import sheets
from app.storage import get_stats

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Yelp Album Tracker", lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"albums": storage.get_albums(), "sheet_url": SHEET_URL, **get_stats()},
    )


@app.post("/scrape")
def scrape(background_tasks: BackgroundTasks, yelp_url: str = Form(...)):
    storage.add_album(yelp_url)
    background_tasks.add_task(run_pipeline, yelp_url)
    return RedirectResponse(url="/", status_code=303)


@app.post("/refresh")
def refresh_one(background_tasks: BackgroundTasks, yelp_url: str = Form(...)):
    background_tasks.add_task(run_pipeline, yelp_url)
    return RedirectResponse(url="/", status_code=303)


@app.post("/scrape-all")
def scrape_all(background_tasks: BackgroundTasks):
    urls = [a["url"] for a in storage.get_albums()]

    def _run_all():
        for url in urls:
            try:
                run_pipeline(url)
            except Exception as exc:
                print(f"[scrape-all] failed for {url!r}: {exc}", flush=True)

    background_tasks.add_task(_run_all)
    return RedirectResponse(url="/", status_code=303)


@app.post("/remove")
def remove(background_tasks: BackgroundTasks, yelp_url: str = Form(...)):
    album = storage.get_album(yelp_url)
    if album and album.get("biz_urls"):
        other_biz_urls: set[str] = set()
        for a in storage.get_albums():
            if a["url"] != yelp_url:
                other_biz_urls.update(a.get("biz_urls", []))
        to_remove = [u for u in album["biz_urls"] if u not in other_biz_urls]
        if to_remove:
            background_tasks.add_task(sheets.remove_businesses, to_remove)
    storage.remove_album(yelp_url)
    return RedirectResponse(url="/", status_code=303)

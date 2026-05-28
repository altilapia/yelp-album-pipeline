from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import storage
from app.pipeline import run_pipeline
from app.scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        context={"albums": storage.get_albums()},
    )


@app.post("/scrape")
def scrape(background_tasks: BackgroundTasks, yelp_url: str = Form(...)):
    storage.add_album(yelp_url)
    background_tasks.add_task(run_pipeline, yelp_url)
    return RedirectResponse(url="/", status_code=303)


@app.post("/scrape-all")
def scrape_all(background_tasks: BackgroundTasks):
    for url in storage.get_albums():
        background_tasks.add_task(run_pipeline, url)
    return RedirectResponse(url="/", status_code=303)

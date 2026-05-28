from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app import storage
from app.config import SCHEDULE_TIME
from app.pipeline import run_pipeline


def run_all() -> None:
    """Run the pipeline for every tracked album URL."""
    for url in storage.get_albums():
        try:
            run_pipeline(url)
        except Exception as exc:
            print(f"[scheduler] pipeline failed for {url!r}: {exc}", flush=True)


def create_scheduler() -> BackgroundScheduler:
    hour, minute = SCHEDULE_TIME.split(":")
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_all, "cron", hour=int(hour), minute=int(minute))
    return scheduler

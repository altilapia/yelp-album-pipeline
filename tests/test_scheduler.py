from unittest.mock import call, patch

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.scheduler import create_scheduler, run_all


# ── run_all ───────────────────────────────────────────────────────────────────

def test_run_all_calls_pipeline_for_each_url():
    urls = ["https://url1.example.com", "https://url2.example.com"]
    with patch("app.scheduler.storage") as ms, patch("app.scheduler.run_pipeline") as mp:
        ms.get_albums.return_value = urls
        run_all()
    mp.assert_has_calls([call(urls[0]), call(urls[1])])
    assert mp.call_count == 2


def test_run_all_does_nothing_when_no_albums():
    with patch("app.scheduler.storage") as ms, patch("app.scheduler.run_pipeline") as mp:
        ms.get_albums.return_value = []
        run_all()
    mp.assert_not_called()


def test_run_all_continues_after_one_failure():
    urls = ["https://fail.example.com", "https://ok.example.com"]

    def fail_first(url):
        if url == urls[0]:
            raise RuntimeError("scrape blocked")

    with patch("app.scheduler.storage") as ms, patch("app.scheduler.run_pipeline", side_effect=fail_first) as mp:
        ms.get_albums.return_value = urls
        run_all()  # must not raise

    assert mp.call_count == 2


def test_run_all_does_not_propagate_exception():
    with patch("app.scheduler.storage") as ms, patch("app.scheduler.run_pipeline", side_effect=Exception("boom")):
        ms.get_albums.return_value = ["https://url.example.com"]
        run_all()  # must not raise


# ── create_scheduler ──────────────────────────────────────────────────────────

@pytest.fixture
def scheduler():
    # create_scheduler() configures but does not start the scheduler
    return create_scheduler()


def test_create_scheduler_returns_background_scheduler(scheduler):
    assert isinstance(scheduler, BackgroundScheduler)


def test_create_scheduler_has_exactly_one_job(scheduler):
    assert len(scheduler.get_jobs()) == 1


def test_create_scheduler_job_function_is_run_all(scheduler):
    assert scheduler.get_jobs()[0].func is run_all


def test_create_scheduler_uses_cron_trigger(scheduler):
    assert isinstance(scheduler.get_jobs()[0].trigger, CronTrigger)


def test_create_scheduler_reads_schedule_time():
    with patch("app.scheduler.SCHEDULE_TIME", "14:30"):
        s = create_scheduler()
    job = s.get_jobs()[0]
    trigger = job.trigger
    hour_field = next(f for f in trigger.fields if f.name == "hour")
    minute_field = next(f for f in trigger.fields if f.name == "minute")
    assert str(hour_field) == "14"
    assert str(minute_field) == "30"

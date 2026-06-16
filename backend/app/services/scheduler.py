import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler():
    s = get_scheduler()
    if not s.running:
        s.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    s = get_scheduler()
    if s.running:
        s.shutdown(wait=False)
        logger.info("Scheduler stopped")


def schedule_ip_expiry(ip: str, expires_at: datetime, callback):
    s = get_scheduler()
    job_id = f"expire_{ip}"

    if s.get_job(job_id):
        s.remove_job(job_id)

    s.add_job(
        callback,
        trigger=DateTrigger(run_date=expires_at),
        id=job_id,
        args=[ip],
        name=f"Expire IP {ip}",
        misfire_grace_time=60,
        replace_existing=True,
    )
    logger.info(f"Scheduled expiry: {ip} at {expires_at.isoformat()}")


def cancel_ip_expiry(ip: str):
    s = get_scheduler()
    job_id = f"expire_{ip}"
    if s.get_job(job_id):
        s.remove_job(job_id)
        logger.info(f"Cancelled expiry: {ip}")


def list_scheduled_jobs() -> list[dict]:
    s = get_scheduler()
    return [
        {
            "id": j.id,
            "name": j.name,
            "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
        }
        for j in s.get_jobs()
    ]

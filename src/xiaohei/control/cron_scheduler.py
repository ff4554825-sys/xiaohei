from typing import Dict, Callable, Any, Optional
from uuid import UUID, uuid4
import asyncio
import schedule
import time
from datetime import datetime
from filelock import FileLock
import os
from loguru import logger


class CronJob:
    def __init__(self, func: Callable, schedule_str: str, args: tuple = (), kwargs: dict = {}):
        self.id = uuid4()
        self.func = func
        self.schedule_str = schedule_str
        self.args = args
        self.kwargs = kwargs
        self.next_run: Optional[datetime] = None


class CronScheduler:
    def __init__(self, data_dir: str = "./data"):
        self._jobs: Dict[UUID, CronJob] = {}
        self._scheduler = schedule.Scheduler()
        self._lock_file = os.path.join(data_dir, "cron.lock")
        self._lock = FileLock(self._lock_file, timeout=10)
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        logger.info("CronScheduler initialized")

    def add_job(self, func: Callable, schedule_str: str, *args, **kwargs) -> UUID:
        job = CronJob(func, schedule_str, args, kwargs)

        if schedule_str.startswith("every"):
            parts = schedule_str.split()
            interval = int(parts[1])
            unit = parts[2] if len(parts) > 2 else "seconds"

            if unit == "seconds":
                self._scheduler.every(interval).seconds.do(self._wrap_job(job))
            elif unit == "minutes":
                self._scheduler.every(interval).minutes.do(self._wrap_job(job))
            elif unit == "hours":
                self._scheduler.every(interval).hours.do(self._wrap_job(job))
            elif unit == "days":
                self._scheduler.every(interval).days.do(self._wrap_job(job))
            elif unit == "week":
                self._scheduler.every(interval).week.do(self._wrap_job(job))
        elif "at" in schedule_str:
            parts = schedule_str.split("at")
            time_str = parts[1].strip()
            self._scheduler.every().day.at(time_str).do(self._wrap_job(job))

        self._jobs[job.id] = job
        logger.info(f"Cron job added: {job.id} - {schedule_str}")
        return job.id

    def _wrap_job(self, job: CronJob):
        def wrapper():
            try:
                with self._lock:
                    logger.debug(f"Executing cron job: {job.id}")
                    if asyncio.iscoroutinefunction(job.func):
                        if self._loop:
                            self._loop.create_task(job.func(*job.args, **job.kwargs))
                        else:
                            asyncio.run(job.func(*job.args, **job.kwargs))
                    else:
                        job.func(*job.args, **job.kwargs)
                logger.debug(f"Cron job completed: {job.id}")
            except Exception as e:
                logger.error(f"Cron job failed: {job.id} - {e}")

        return wrapper

    def remove_job(self, job_id: UUID) -> bool:
        if job_id in self._jobs:
            job = self._jobs.pop(job_id)
            self._scheduler.cancel_job(
                next((j for j in self._scheduler.jobs if j.job_func.__name__ == str(job.id)), None)
            )
            logger.info(f"Cron job removed: {job_id}")
            return True
        return False

    def list_jobs(self) -> Dict[UUID, CronJob]:
        return dict(self._jobs)

    async def start(self) -> None:
        if self._running:
            logger.warning("Cron scheduler already running")
            return

        self._running = True
        self._loop = asyncio.get_event_loop()
        logger.info("Cron scheduler started")

        while self._running:
            self._scheduler.run_pending()
            await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False
        logger.info("Cron scheduler stopped")

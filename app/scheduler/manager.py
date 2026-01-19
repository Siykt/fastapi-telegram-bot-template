"""
调度管理器

基于 APScheduler 的统一调度管理器，负责：
- 调度器生命周期管理
- 任务注册与管理
- 任务执行日志
- 分布式锁支持（多实例部署）
"""

import functools
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logger import get_module_logger

# 使用模块化日志 - 日志会同时写入 app.log 和 scheduler.log
logger = get_module_logger("scheduler")


# =============================================================================
# 分布式锁配置
# =============================================================================

# 锁 Key 前缀
LOCK_KEY_PREFIX = "scheduler:lock:"

# 默认锁超时时间（秒）
DEFAULT_LOCK_TTL = 300

# Lua 脚本：安全释放锁（只有锁的所有者才能释放）
RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class SchedulerManager:
    """
    调度管理器

    统一管理所有定时任务的注册、启动、停止。
    支持分布式锁，确保多实例部署时任务不重复执行。
    """

    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running: bool = False
        self._release_lock_sha: str | None = None  # Lua 脚本 SHA

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """获取调度器实例"""
        if self._scheduler is None:
            raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
        return self._scheduler

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._is_running

    def init(self) -> None:
        """
        初始化调度器

        配置调度器参数，但不启动。
        """
        if self._scheduler is not None:
            logger.warning("Scheduler already initialized")
            return

        self._scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # 任务堆积时是否合并执行
                "max_instances": 1,  # 每个任务最多同时运行1个实例
                "misfire_grace_time": 60,  # 错过执行时间的容忍秒数
            },
        )

        # 注册事件监听
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)

        logger.info("Scheduler initialized")

    async def start(self) -> None:
        """
        启动调度器

        注册所有任务并启动调度器。
        """
        if self._scheduler is None:
            self.init()

        if self._is_running:
            logger.warning("Scheduler already running")
            return

        # 注册所有任务
        self._register_jobs()

        # 启动调度器
        self._scheduler.start()
        self._is_running = True

        logger.info(f"Scheduler started with {len(self._scheduler.get_jobs())} jobs")

    async def stop(self) -> None:
        """
        停止调度器

        优雅关闭，等待当前任务完成。
        """
        if not self._is_running:
            return

        if self._scheduler:
            self._scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("Scheduler stopped")

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        *,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        start_date: datetime | None = None,
        replace_existing: bool = True,
        distributed: bool = True,
        lock_ttl: int = DEFAULT_LOCK_TTL,
        **kwargs,
    ) -> None:
        """
        添加间隔任务

        Args:
            func: 任务函数（async function）
            job_id: 任务唯一标识
            seconds: 间隔秒数
            minutes: 间隔分钟数
            hours: 间隔小时数
            start_date: 首次执行时间
            replace_existing: 是否替换已存在的同名任务
            distributed: 是否启用分布式锁（默认 True）
            lock_ttl: 锁超时时间（秒），默认 300s
            **kwargs: 传递给任务函数的参数
        """
        trigger = IntervalTrigger(
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            start_date=start_date,
        )

        # 如果启用分布式锁，包装任务函数
        job_func = func
        if distributed:
            job_func = self._wrap_with_distributed_lock(func, job_id, lock_ttl)

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            replace_existing=replace_existing,
            kwargs=kwargs,
        )

        lock_info = f", distributed_lock=True, ttl={lock_ttl}s" if distributed else ""
        logger.info(f"Added interval job: {job_id} (every {hours}h {minutes}m {seconds}s{lock_info})")

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        *,
        hour: int | None = None,
        minute: int | None = None,
        second: int | None = None,
        day_of_week: str | None = None,
        replace_existing: bool = True,
        distributed: bool = True,
        lock_ttl: int = DEFAULT_LOCK_TTL,
        **kwargs,
    ) -> None:
        """
        添加 Cron 任务

        Args:
            func: 任务函数（async function）
            job_id: 任务唯一标识
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            second: 秒 (0-59)
            day_of_week: 星期几 (mon,tue,wed,thu,fri,sat,sun)
            replace_existing: 是否替换已存在的同名任务
            distributed: 是否启用分布式锁（默认 True）
            lock_ttl: 锁超时时间（秒），默认 300s
            **kwargs: 传递给任务函数的参数
        """
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            second=second,
            day_of_week=day_of_week,
        )

        # 如果启用分布式锁，包装任务函数
        job_func = func
        if distributed:
            job_func = self._wrap_with_distributed_lock(func, job_id, lock_ttl)

        self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            replace_existing=replace_existing,
            kwargs=kwargs,
        )

        lock_info = f", distributed_lock=True, ttl={lock_ttl}s" if distributed else ""
        logger.info(f"Added cron job: {job_id}{lock_info}")

    def remove_job(self, job_id: str) -> bool:
        """
        移除任务

        Args:
            job_id: 任务唯一标识

        Returns:
            bool: 是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception:
            return False

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception:
            return False

    def get_job_info(self, job_id: str) -> dict | None:
        """获取任务信息"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None

        return {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time,
            "trigger": str(job.trigger),
        }

    def list_jobs(self) -> list[dict]:
        """列出所有任务"""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
            for job in self.scheduler.get_jobs()
        ]

    def _register_jobs(self) -> None:
        """
        注册所有定时任务

        在此处集中注册所有需要的定时任务。
        """
        from app.scheduler.jobs import notification_jobs, payment_jobs

        # 支付相关任务
        payment_jobs.register_jobs(self)

        # 通知相关任务
        notification_jobs.register_jobs(self)

        logger.info("All jobs registered")

    def _on_job_executed(self, event: JobEvent) -> None:
        """任务执行成功回调"""
        logger.debug(f"Job executed: {event.job_id}")

    def _on_job_error(self, event: JobEvent) -> None:
        """任务执行失败回调"""
        logger.error(f"Job error: {event.job_id}, exception: {event.exception}")

    # =========================================================================
    # 分布式锁相关方法
    # =========================================================================

    async def _acquire_lock(self, job_id: str, ttl: int = DEFAULT_LOCK_TTL) -> str | None:
        """
        尝试获取分布式锁

        Args:
            job_id: 任务 ID（用于生成锁 Key）
            ttl: 锁超时时间（秒）

        Returns:
            成功返回锁 token，失败返回 None
        """
        from app.core import get_redis

        redis = get_redis()
        lock_key = f"{LOCK_KEY_PREFIX}{job_id}"
        lock_token = str(uuid.uuid4())

        # SET NX EX：仅当 key 不存在时设置，并设置过期时间
        acquired = await redis.set(lock_key, lock_token, nx=True, ex=ttl)

        if acquired:
            logger.debug(f"Distributed lock acquired: job={job_id}, token={lock_token[:8]}")
            return lock_token
        else:
            logger.debug(f"Distributed lock not acquired (already held): job={job_id}")
            return None

    async def _release_lock(self, job_id: str, token: str) -> bool:
        """
        安全释放分布式锁

        使用 Lua 脚本确保只有锁的所有者才能释放。

        Args:
            job_id: 任务 ID
            token: 获取锁时返回的 token

        Returns:
            是否成功释放
        """
        from app.core import get_redis

        redis = get_redis()
        lock_key = f"{LOCK_KEY_PREFIX}{job_id}"

        # 使用 Lua 脚本安全释放锁
        # 缓存脚本 SHA 以提高性能
        if self._release_lock_sha is None:
            self._release_lock_sha = await redis.script_load(RELEASE_LOCK_SCRIPT)

        try:
            result = await redis.evalsha(self._release_lock_sha, 1, lock_key, token)
            released = result == 1

            if released:
                logger.debug(f"Distributed lock released: job={job_id}")
            else:
                logger.warning(f"Distributed lock release failed (not owner): job={job_id}")

            return released
        except Exception as e:
            # 如果脚本不存在（Redis 重启），重新加载
            logger.warning(f"Lock release error, retrying with EVAL: {e}")
            result = await redis.eval(RELEASE_LOCK_SCRIPT, 1, lock_key, token)
            return result == 1

    def _wrap_with_distributed_lock(
        self,
        func: Callable[..., Awaitable[Any]],
        job_id: str,
        lock_ttl: int = DEFAULT_LOCK_TTL,
    ) -> Callable[..., Awaitable[Any]]:
        """
        包装任务函数，添加分布式锁

        Args:
            func: 原始任务函数
            job_id: 任务 ID
            lock_ttl: 锁超时时间

        Returns:
            包装后的函数
        """
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 尝试获取锁
            token = await self._acquire_lock(job_id, lock_ttl)
            if token is None:
                # 获取锁失败，跳过本次执行
                logger.info(f"Job skipped (lock not acquired): {job_id}")
                return None

            try:
                # 执行原始任务
                return await func(*args, **kwargs)
            finally:
                # 无论成功失败，都释放锁
                await self._release_lock(job_id, token)

        return wrapper


# 全局调度管理器实例
scheduler_manager = SchedulerManager()


def init_scheduler() -> None:
    """初始化调度器（在应用启动时调用）"""
    scheduler_manager.init()

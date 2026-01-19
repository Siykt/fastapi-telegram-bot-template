"""日志系统初始化

模块化日志系统:
- 通用日志: logs/app.log (所有日志)
- 错误日志: logs/error.log (ERROR 及以上级别)
- 模块日志: logs/{module}.log (如 payment.log, scheduler.log)

使用方法:
    from app.core.logger import logger, get_module_logger

    # 通用日志
    logger.info("普通日志")

    # 模块日志（同时写入 app.log 和对应模块日志文件）
    payment_logger = get_module_logger("payment")
    payment_logger.info("支付相关日志")
"""

import logging
import os
import sys
from collections.abc import Callable

from loguru import logger as _logger

from app.core.config import settings


# Worker 标识（使用 PID 后三位）
# 注意：不缓存，因为 gunicorn fork 后 PID 会变化
def _get_worker_id() -> str:
    """获取 Worker 标识（PID 后三位）"""
    pid = os.getpid()
    return f"P{pid % 1000:03d}"

# 需要独立日志文件的模块
MODULE_LOG_FILES = ("payment", "pvp", "scheduler", "forge", "cli")

# 模块与第三方库的映射（第三方库日志写入对应模块日志文件）
MODULE_SOURCE_MAPPING = {
    "scheduler": ("[apscheduler]",),
}

# 第三方库 logger 名称前缀
THIRD_PARTY_LOGGERS = frozenset({
    "uvicorn", "fastapi", "starlette", "sqlalchemy", "aiogram",
    "apscheduler", "asyncio", "redis", "aioredis",
    "httpx", "httpcore", "aiohttp", "watchfiles", "websockets", "multipart",
})

# 第三方库日志级别配置
THIRD_PARTY_LOG_LEVELS = {
    "sqlalchemy": "WARNING",
    "sqlalchemy.engine": "WARNING",
    "apscheduler": "WARNING",  # 只显示警告和错误，不显示每次任务执行
    "asyncio": "WARNING",
    "redis": "WARNING",
    "httpx": "WARNING",
    "httpcore": "WARNING",
}


class InterceptHandler(logging.Handler):
    """拦截标准 logging 并转发到 loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        top_module = (record.name or "unknown").split(".")[0]

        if top_module in THIRD_PARTY_LOGGERS:
            # 第三方库：显示 [库名] 格式
            _logger.bind(source=f"[{top_module}]").opt(
                exception=record.exc_info
            ).log(level, record.getMessage())
        else:
            # 使用 record 自带的调用位置信息（logging 已经计算好了真实调用者）
            filename = os.path.basename(record.pathname)
            source = f"{filename}:{record.funcName}:{record.lineno}"
            _logger.bind(source=source).opt(exception=record.exc_info).log(
                level, record.getMessage()
            )


def _get_location(record: dict) -> str:
    """获取日志位置信息"""
    extra = record["extra"]
    if "source" in extra:
        return extra["source"]
    return f"{record['name']}:{record['function']}:{record['line']}"


def _console_format(record: dict) -> str:
    """控制台格式（带颜色）"""
    location = _get_location(record)
    worker_id = _get_worker_id()
    return (
        f"<green>{{time:YYYY-MM-DD HH:mm:ss}}</green> | "
        f"<level>{{level: <8}}</level> | "
        f"<yellow>[{worker_id}]</yellow> | "
        f"<cyan>{location}</cyan> | "
        f"<level>{{message}}</level>\n"
    )


def _file_format(record: dict) -> str:
    """文件格式（纯文本）"""
    location = _get_location(record)
    worker_id = _get_worker_id()
    return (
        f"{{time:YYYY-MM-DD HH:mm:ss}} | "
        f"{{level: <8}} | "
        f"[{worker_id}] | "
        f"{location} | "
        f"{{message}}\n"
    )


def _create_module_filter(module_name: str) -> Callable[[dict], bool]:
    """创建模块日志过滤器"""
    allowed_sources = MODULE_SOURCE_MAPPING.get(module_name, ())

    def _filter(record: dict) -> bool:
        extra = record.get("extra", {})
        return (
            extra.get("module") == module_name or
            extra.get("source") in allowed_sources
        )
    return _filter


def init_logger() -> None:
    """初始化日志系统"""
    _logger.remove()

    # 控制台输出
    _logger.add(
        sys.stderr,
        format=_console_format,
        level=settings.log.level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )
    # 错误日志（只记录 ERROR 及以上级别）
    _logger.add(
        "logs/error.log",
        format=_file_format,
        level="ERROR",
        rotation=settings.log.rotation,
        retention=settings.log.retention,
        compression="zip",
        backtrace=True,
        diagnose=True,  # 错误日志开启详细诊断
    )
    # 文件输出（非 debug 模式）
    if not settings.debug:
        file_config = {
            "format": _file_format,
            "level": settings.log.level,
            "rotation": settings.log.rotation,
            "retention": settings.log.retention,
            "compression": "zip",
            "backtrace": True,
            "diagnose": False,
        }

        # 通用日志
        _logger.add("logs/app.log", **file_config)
        # 模块日志
        for module_name in MODULE_LOG_FILES:
            _logger.add(
                f"logs/{module_name}.log",
                filter=_create_module_filter(module_name),
                **file_config,
            )

    # 拦截标准 logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 配置第三方库日志级别
    for name, level in THIRD_PARTY_LOG_LEVELS.items():
        _configure_logger(name, level)

    # 配置其他第三方库使用默认级别
    default_loggers = [
        "uvicorn", "uvicorn.error", "uvicorn.access",
        "fastapi", "aiogram", "aiogram.event", "aiogram.dispatcher",
    ]
    for name in default_loggers:
        _configure_logger(name, settings.log.level)

    # sqlalchemy.engine 特殊处理
    if settings.database.echo:
        _configure_logger("sqlalchemy.engine", "INFO")

    _logger.info("Logger initialized")


def _configure_logger(name: str, level: str) -> None:
    """配置单个 logger"""
    log = logging.getLogger(name)
    log.setLevel(level)
    log.handlers = [InterceptHandler()]
    log.propagate = False


def get_module_logger(module_name: str):
    """获取模块 logger

    日志会写入 logs/app.log，如果模块在 MODULE_LOG_FILES 中，
    还会写入 logs/{module}.log
    """
    return _logger.bind(module=module_name)


# 导出
logger = _logger

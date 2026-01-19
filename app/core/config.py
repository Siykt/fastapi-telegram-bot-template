"""Application settings loaded from YAML configuration files."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, RootModel


class DatabaseSettings(BaseModel):
    """数据库配置。"""

    url: str = Field(default="mysql+asyncmy://user:pass@localhost:3306/hitcards", description="数据库连接URL, 必填")
    username: str = Field(default="user", description="数据库用户名, 必填")
    password: str = Field(default="pass", description="数据库密码, 必填")
    pool_size: int = Field(default=10, ge=1, description="连接池大小, 可选, 默认10")
    max_overflow: int = Field(default=20, ge=0, description="连接池最大溢出数, 可选, 默认20")
    pool_timeout: float = Field(default=30, ge=0, description="连接池超时时间, 可选, 默认30秒")
    echo: bool = Field(default=False, description="是否打印SQL语句, 可选, 默认False")

    def get_db_url(self) -> str:
        """获取数据库连接URL。"""
        # 对用户名和密码进行 URL 编码，处理特殊字符（如 #, $, %, ^ 等）
        encoded_user = quote_plus(self.username)
        encoded_password = quote_plus(self.password)
        return self.url + f"?user={encoded_user}&password={encoded_password}"


class RedisSettings(BaseModel):
    """Redis配置。"""

    url: str = Field(default="redis://localhost:6379/0", description="Redis连接URL, 必填")


class BotConfig(BaseModel):
    """单个Bot配置。"""

    name: str = Field(description="Bot名称")
    token: str = Field(description="Telegram Bot Token")
    mode: str = Field(default="polling", description="运行模式: polling/webhook/dev")
    webhook_url: str | None = Field(default=None, description="Webhook URL(webhook模式必填)")
    bot_url: str | None = Field(default=None, description="Bot链接")
    app_url: str | None = Field(default=None, description="Mini App URL")


class BotSettings(RootModel[list[BotConfig]]):
    """Bot配置管理。"""

    root: list[BotConfig] = []

    def __iter__(self):
        return iter(self.root)

    def __len__(self):
        return len(self.root)

    def get_main_bot(self) -> BotConfig | None:
        """获取主Bot配置（第一个）。"""
        return self.root[0] if self.root else None

    def get_by_name(self, name: str) -> BotConfig | None:
        """根据名称获取Bot配置。"""
        for bot in self.root:
            if bot.name == name:
                return bot
        return None


class LogSettings(BaseModel):
    """日志配置。"""

    level: str = Field(default="INFO", description="日志级别(DEBUG/INFO/WARNING/ERROR/CRITICAL), 可选, 默认INFO")
    format: str = Field(default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>", description="日志格式, 可选")
    rotation: str = Field(default="10 MB", description="日志轮转大小, 可选, 默认10 MB")
    retention: str = Field(default="7 days", description="日志保留时间, 可选, 默认7 days")


class Settings(BaseModel):
    """应用配置。"""

    env: str = Field(default="dev", description="当前环境(dev/test/prod), 可选, 默认dev")
    app_name: str = Field(default="FastApiTelegramBotTemplate", description="应用名称, 可选, 默认FastApiTelegramBotTemplate")
    debug: bool = Field(default=False, description="调试模式, 可选, 默认False")
    secret_key: str = Field(default="your-secret-key-change-in-production", description="密钥, 必填")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings, description="数据库配置")
    redis: RedisSettings = Field(default_factory=RedisSettings, description="Redis配置")
    bots: BotSettings = Field(default_factory=BotSettings, description="Bot配置列表")
    log: LogSettings = Field(default_factory=LogSettings, description="日志配置")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _get_project_root() -> Path:
    """Get project root directory (where main.py is located)."""
    return Path(__file__).parent.parent.parent


def _load_yaml_config(env: str) -> dict[str, Any]:
    """Load YAML configuration for the specified environment."""
    project_root = _get_project_root()

    base_config: dict[str, Any] = {}
    base_file = project_root / "base.config.yml"
    if base_file.exists():
        with open(base_file, encoding="utf-8") as f:
            base_config = yaml.safe_load(f) or {}

    env_config: dict[str, Any] = {}
    env_file = project_root / f"{env}.config.yml"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            env_config = yaml.safe_load(f) or {}

    merged = _deep_merge(base_config, env_config)
    merged["env"] = env
    return merged


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance based on APP_ENV environment variable."""
    env = os.getenv("APP_ENV", "dev")
    config_data = _load_yaml_config(env)
    return Settings(**config_data)


def reload_settings(env: str | None = None) -> Settings:
    """Reload settings with a new environment.

    Args:
        env: Environment name (dev/test/prod). If None, uses APP_ENV env var.

    Returns:
        New Settings instance
    """
    if env is not None:
        os.environ["APP_ENV"] = env
    get_settings.cache_clear()
    new_settings = get_settings()
    # Update the module-level settings reference
    global settings
    settings = new_settings
    return new_settings


def get_current_env() -> str:
    """Get current environment name."""
    return os.getenv("APP_ENV", "dev")


settings = get_settings()

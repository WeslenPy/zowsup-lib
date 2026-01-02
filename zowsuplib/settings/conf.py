from pathlib import Path
from typing import Optional, Set

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Global application settings, loaded via Pydantic BaseSettings.

    This replaces direct usage of os.environ. Values can come from:
    - environment variables (prefix: ZOWSUP_)
    - a .env file in the project root
    - default values defined here
    """

    # Arquivo principal de configuração (mesma semântica do antigo ZOWSUP_CONFIG)
    config: str = Field(default="conf/config.conf", env="ZOWSUP_CONFIG")

    # Caminhos principais
    account_path: Path = Field(default=Path("/data/account/"), env="ZOWSUP_ACCOUNT_PATH")
    download_path: Path = Field(default=Path("/data/download/"), env="ZOWSUP_DOWNLOAD_PATH")
    upload_path: Path = Field(default=Path("/data/upload/"), env="ZOWSUP_UPLOAD_PATH")
    log_path: Path = Field(default=Path("/data/log/"), env="ZOWSUP_LOG_PATH")
    default_env: str = Field(default="android", env="ZOWSUP_DEFAULT_ENV")
    cmd_wait: Optional[int] = Field(default=None, env="ZOWSUP_CMD_WAIT")

    # Database – single DB file in the project root by default (SQLite)
    db_url: str = Field(
        default="sqlite:///zowsup.db",
        description="SQLAlchemy DB URL. Defaults to a single SQLite file 'zowsup.db' in the project root.",
        env="ZOWSUP_DB_URL",
    )
    db_pool_size: int = Field(
        default=100,
        description="Base pool size for SQLAlchemy engine (ignored for SQLite).",
        env="ZOWSUP_DB_POOL_SIZE",
    )
    db_max_overflow: int = Field(
        default=40,
        description="Max overflow connections above pool_size (ignored for SQLite).",
        env="ZOWSUP_DB_MAX_OVERFLOW",
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Seconds to wait for a connection from the pool (ignored for SQLite).",
        env="ZOWSUP_DB_POOL_TIMEOUT",
    )
    db_pool_recycle: int = Field(
        default=1800,
        description="Seconds before recycling a connection (ignored for SQLite).",
        env="ZOWSUP_DB_POOL_RECYCLE",
    )

    # Storage backend selector (mantido por compatibilidade)
    storage_backend: str = Field(
        default="sqlalchemy",
        description="Storage backend selector (reserved, currently always uses the unified SQLAlchemy schema).",
        env="ZOWSUP_STORAGE_BACKEND",
    )

    # Proxy (mantém compat com http_proxy/https_proxy via env list)
    http_proxy: Optional[str] = Field(default=None, env=["ZOWSUP_HTTP_PROXY", "http_proxy", "HTTP_PROXY"])
    https_proxy: Optional[str] = Field(default=None, env=["ZOWSUP_HTTPS_PROXY", "https_proxy", "HTTPS_PROXY"])

    debug_break_flags: Set[str] = Field(default_factory=set, env="ZOWSUP_DEBUG_BREAK_FLAGS")

    @field_validator("debug_break_flags", mode="before")
    @classmethod
    def _split_flags(cls, v):
        if v is None or v == "":
            return set()
        if isinstance(v, (list, set, tuple)):
            return {str(item).strip() for item in v if str(item).strip()}
        if isinstance(v, str):
            return {item.strip() for item in v.split(",") if item.strip()}
        return set()

    class Config:
        env_prefix = "ZOWSUP_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

# Singleton settings instance used across the application
settings = Settings()



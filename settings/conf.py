from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Global application settings, loaded via Pydantic BaseSettings.

    This replaces direct usage of os.environ. Values can come from:
    - environment variables (prefix: ZOWSUP_)
    - a .env file in the project root
    - default values defined here
    """

    # Database – single DB file in the project root by default (SQLite)
    # Example override in .env:
    #   ZOWSUP_DB_URL=sqlite:///zowsup.db
    #   or any SQLAlchemy‑compatible URL.
    db_url: str = Field(
        default="sqlite:///zowsup.db",
        description="SQLAlchemy DB URL. Defaults to a single SQLite file 'zowsup.db' in the project root.",
    )
    # Pool configuration (used for non-SQLite backends)
    db_pool_size: int = Field(
        default=20,
        description="Base pool size for SQLAlchemy engine (ignored for SQLite).",
    )
    db_max_overflow: int = Field(
        default=40,
        description="Max overflow connections above pool_size (ignored for SQLite).",
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Seconds to wait for a connection from the pool (ignored for SQLite).",
    )
    db_pool_recycle: int = Field(
        default=1800,
        description="Seconds before recycling a connection (ignored for SQLite).",
    )

    # Storage backend for Axolotl data – we now use a single DB schema (SqlAxolotlStore).
    # This field is kept for future extension but currently ignored.
    storage_backend: str = Field(
        default="sqlalchemy",
        description='Storage backend selector (reserved, currently always uses the unified SQLAlchemy schema).',
    )
    
    config: str = Field(
        default="conf/config.conf", description='Arquivo de configuração da aplicação.'
    )

    class Config:
        env_prefix = "ZOWSUP_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton settings instance used across the application
settings = Settings()

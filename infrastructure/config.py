from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///./taxibek.db"
    redis_url: str = ""
    admin_ids: list[int] = Field(default_factory=list)
    webapp_url: str = ""
    default_route_id: int = 1
    contact_phone: str = "+998909717870"

    admin_phone: str = ""
    admin_password: str = ""
    session_ttl_seconds: int = 86400
    session_secure_cookie: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

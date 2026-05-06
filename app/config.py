from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "AlphaOS"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str
    redis_url: str

    bags_api_base_url: str = "https://api.bags.fm"
    bags_api_key: str

    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"

    anthropic_api_key: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24

    twitter_bearer_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
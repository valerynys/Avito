from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    server_address: str
    postgres_conn: str
    postgres_jdbc_url: str
    postgres_username: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_database: str

    model_config = SettingsConfigDict(env_file=".env")


def get_settings():
    return Settings()


settings = get_settings()

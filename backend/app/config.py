from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://jass:jass@db:5432/jass"

    class Config:
        env_file = ".env"


settings = Settings()

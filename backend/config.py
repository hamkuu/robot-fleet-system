from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    CLOUD_SQL_CONNECTION_NAME: str | None = None

    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_TOPIC: str = "images/+/captures"
    MQTT_CLIENT_ID: str = "image-subscriber"

    @property
    def DATABASE_URL(self) -> URL:
        if self.CLOUD_SQL_CONNECTION_NAME:
            return URL.create(
                "postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                database=self.POSTGRES_DB,
                query={
                    "host": f"/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}",
                },
            )

        return URL.create(
            "postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

    model_config = SettingsConfigDict(env_file="../.env")


settings = Settings()

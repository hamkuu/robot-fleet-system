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
        socket_path = (
            f"/cloudsql/{self.CLOUD_SQL_CONNECTION_NAME}"
            if self.CLOUD_SQL_CONNECTION_NAME
            else None
        )

        return URL.create(
            "postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=None if socket_path else self.POSTGRES_SERVER,
            port=None if socket_path else self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
            query={"host": socket_path} if socket_path else {},
        )

    model_config = SettingsConfigDict(env_file="../.env")


settings = Settings()

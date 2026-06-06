from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://complex:complex@db:5432/waste_complex"
    cors_origins: str = "http://localhost:8080,http://localhost:5173,http://localhost:3000"
    jwt_secret: str = "waste-complex-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    file_storage_root: str = "/app/storage"
    max_upload_bytes: int = 20 * 1024 * 1024
    allow_public_registration: bool = Field(
        default=True,
        description="Разрешить POST /auth/register без ограничения «только первый пользователь»",
        validation_alias=AliasChoices(
            "ALLOW_PUBLIC_REGISTRATION",
            "PUBLIC_REGISTER_ENABLED",
        ),
    )
    firebase_credentials_path: str = Field(
        default="",
        description="Путь к JSON сервисного аккаунта Firebase Admin SDK",
        validation_alias=AliasChoices(
            "FIREBASE_CREDENTIALS_PATH",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ),
    )


settings = Settings()

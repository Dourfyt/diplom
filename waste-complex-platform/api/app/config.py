from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://complex:complex@db:5432/waste_complex"
    cors_origins: str = "http://localhost:8080,http://localhost:5173,http://localhost:3000"
    jwt_secret: str = "waste-complex-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


settings = Settings()

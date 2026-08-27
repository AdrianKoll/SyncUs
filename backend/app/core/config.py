import os
import secrets
from typing import ClassVar, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Finance Couple App"
    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias
    CORS_ORIGINS: str = ""

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "casal_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "casal_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "casal_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    _placeholder_secrets: ClassVar[set[str]] = {
        "sua_chave_secret_muito_segura_aqui",
        "sua_chave_secreta_super_segura_gerada_aqui",
        "change-me",
        "changeme",
        "secret",
        "test-secret",
    }
    _development_origins: ClassVar[tuple[str, ...]] = (
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    )

    @model_validator(mode="after")
    def validate_security_settings(self):
        secret_key = (self.SECRET_KEY or "").strip()
        if not secret_key:
            if self.ENVIRONMENT == "development":
                # Apenas o desenvolvimento pode gerar uma chave efêmera. Isso
                # evita uma chave previsível, mas invalida sessões ao reiniciar.
                secret_key = secrets.token_urlsafe(48)
            else:
                raise ValueError(
                    "SECRET_KEY é obrigatória fora do ambiente de desenvolvimento"
                )

        if secret_key.lower() in self._placeholder_secrets:
            raise ValueError("SECRET_KEY não pode usar um valor de exemplo ou previsível")

        if self.ENVIRONMENT != "development" and len(secret_key) < 32:
            raise ValueError(
                "SECRET_KEY deve possuir pelo menos 32 caracteres fora do desenvolvimento"
            )
        if self.ENVIRONMENT != "development" and len(set(secret_key)) < 8:
            raise ValueError(
                "SECRET_KEY parece fraca; use uma chave aleatória com maior diversidade"
            )

        self.SECRET_KEY = secret_key

        origins = self.cors_origins
        if self.ENVIRONMENT != "development" and not origins:
            raise ValueError(
                "CORS_ORIGINS deve conter ao menos uma origem explícita fora do desenvolvimento"
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        raw_origins = [origin.strip().rstrip("/") for origin in self.CORS_ORIGINS.split(",")]
        origins = [origin for origin in raw_origins if origin]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS não pode usar wildcard (*)")
        if not origins and self.ENVIRONMENT == "development":
            return list(self._development_origins)
        return origins


settings = Settings()

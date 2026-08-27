import pytest
from pydantic import ValidationError

from app.core.config import Settings


VALID_PRODUCTION_SECRET = "production-secret-with-at-least-32-characters"


def test_development_generates_ephemeral_secret_and_local_origins():
    settings = Settings(
        ENVIRONMENT="development",
        SECRET_KEY=None,
        CORS_ORIGINS="",
    )

    assert len(settings.SECRET_KEY) >= 32
    assert settings.cors_origins == [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


def test_production_requires_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY é obrigatória"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=None,
            CORS_ORIGINS="https://app.example.com",
        )


def test_production_rejects_placeholder_and_short_secret():
    with pytest.raises(ValidationError, match="valor de exemplo"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="sua_chave_secreta_super_segura_gerada_aqui",
            CORS_ORIGINS="https://app.example.com",
        )

    with pytest.raises(ValidationError, match="pelo menos 32 caracteres"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret",
            CORS_ORIGINS="https://app.example.com",
        )

    with pytest.raises(ValidationError, match="parece fraca"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 64,
            CORS_ORIGINS="https://app.example.com",
        )


def test_production_requires_explicit_cors_origins():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=VALID_PRODUCTION_SECRET,
            CORS_ORIGINS="",
        )

    with pytest.raises(ValidationError, match="wildcard"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=VALID_PRODUCTION_SECRET,
            CORS_ORIGINS="*",
        )


def test_production_accepts_explicit_cors_origins_and_strips_trailing_slash():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=VALID_PRODUCTION_SECRET,
        CORS_ORIGINS="https://app.example.com/, https://admin.example.com",
    )

    assert settings.cors_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]

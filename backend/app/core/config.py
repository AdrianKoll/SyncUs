import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Finance Couple App"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "SUA_CHAVE_SECRET_MUITO_SEGURA_AQUI")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias
    
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "casal_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "casal_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "casal_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

settings = Settings()

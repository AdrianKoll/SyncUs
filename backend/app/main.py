from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import engine, Base
from .api import auth, users, transactions
from .websockets import sync
from app.api.couple import router as couple_router
from .models import models  # noqa: F401  # registra os modelos no metadata do SQLAlchemy
from .core.database import SessionLocal
from .services.room_service import ensure_active_connection_members

# Criar tabelas
Base.metadata.create_all(bind=engine)

# Preencher os membros das conexões legadas e validar a nova invariante.
with SessionLocal() as db:
    ensure_active_connection_members(db)

app = FastAPI(title="Finance Couple API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(users.router, prefix="/api/users", tags=["Usuários"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transações"])
app.include_router(sync.router, prefix="/ws", tags=["Sincronização"])
app.include_router(couple_router)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API de Controle Financeiro para Casal"}

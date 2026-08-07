from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, Base
from .api import auth, users, transactions
from .websockets import sync
from app.api.couple import router as couple_router
from .models import models # Importar para garantir que o Base as conheça

# Criar tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Couple API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.models import User, Transaction, Category, Room
from ..schemas.transaction import TransactionCreate, Transaction as TransactionSchema, DashboardSummary, Category as CategorySchema

router = APIRouter()

@router.post("/", response_model=TransactionSchema)
def create_transaction(
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.room_id:
        raise HTTPException(status_code=400, detail="Você precisa estar em uma sala para realizar lançamentos")
    
    db_transaction = Transaction(
        **transaction_in.dict(),
        room_id=current_user.room_id,
        user_id=current_user.id
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.get("/", response_model=List[TransactionSchema])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    if not current_user.room_id:
        return []
    return db.query(Transaction).filter(Transaction.room_id == current_user.room_id).order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.room_id:
        return {
            "total_balance": 0,
            "monthly_income": 0,
            "monthly_expenses": 0,
            "monthly_balance": 0,
            "debt_summary": "Desconectado"
        }
    
    room_id = current_user.room_id
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    
    transactions = db.query(Transaction).filter(Transaction.room_id == room_id).all()
    
    total_balance = sum(t.amount if t.type == 'entrada' else -t.amount for t in transactions)
    
    monthly_txs = [t for t in transactions if t.date >= start_of_month]
    monthly_income = sum(t.amount for t in monthly_txs if t.type == 'entrada')
    monthly_expenses = sum(t.amount for t in monthly_txs if t.type == 'saida')
    monthly_balance = monthly_income - monthly_expenses
    
    # Lógica simplificada de dívida (quem pagou o quê)
    # Aqui poderíamos calcular o saldo entre user1 e user2 baseado no split_type
    debt_summary = "Tudo em dia" # Placeholder
    
    return {
        "total_balance": total_balance,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_balance": monthly_balance,
        "debt_summary": debt_summary
    }

@router.get("/categories", response_model=List[CategorySchema])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Categorias padrão + categorias da sala
    return db.query(Category).filter((Category.room_id == None) | (Category.room_id == current_user.room_id)).all()

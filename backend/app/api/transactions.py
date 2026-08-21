from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.models import User, Transaction, Category, Room
from ..schemas.transaction import (
    TransactionCreate, 
    TransactionUpdate, 
    Transaction as TransactionSchema, 
    DashboardSummary, 
    Category as CategorySchema
)

router = APIRouter()

# 📥 CRIAR LANÇAMENTO
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

# 📋 LISTAR LANÇAMENTOS DO CASAL
@router.get("/", response_model=List[TransactionSchema])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    if not current_user.room_id:
        return []
    
    return db.query(Transaction).filter(
        Transaction.room_id == current_user.room_id
    ).order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

# 📝 ATUALIZAR LANÇAMENTO
@router.put("/{transaction_id}", response_model=TransactionSchema)
def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Busca a transação e garante que ela pertence à sala do casal
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.room_id == current_user.room_id
    ).first()

    if not db_transaction:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado ou acesso negado")

    # Atualiza apenas os campos enviados
    update_data = transaction_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)

    db.commit()
    db.refresh(db_transaction)
    return db_transaction

# 🗑️ EXCLUIR LANÇAMENTO
@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Busca a transação e garante que ela pertence à sala do casal
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.room_id == current_user.room_id
    ).first()

    if not db_transaction:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado ou acesso negado")

    db.delete(db_transaction)
    db.commit()
    return {"message": "Lançamento excluído com sucesso"}

# 📊 DASHBOARD COMPLETO (Saldos, Gráficos e Transações Recentes)
@router.get("/dashboard", response_model=dict)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.room_id:
        return {
            "summary": {"total_balance": 0, "monthly_income": 0, "monthly_expenses": 0, "debt_summary": "Desconectado"},
            "categories": [],
            "recent": [],
            "chart_data": {"labels": [], "income": [], "expenses": []}
        }

    room_id = current_user.room_id
    
    # 1. Totais para os Cards de Topo
    income = db.query(func.sum(Transaction.amount)).filter(
        Transaction.room_id == room_id, Transaction.type == 'entrada'
    ).scalar() or 0

    expenses = db.query(func.sum(Transaction.amount)).filter(
        Transaction.room_id == room_id, Transaction.type == 'saida'
    ).scalar() or 0

    # 2. Gastos por Categoria (Para o gráfico de Rosca)
    categories_data = db.query(
        Category.name, 
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id)\
     .filter(Transaction.room_id == room_id, Transaction.type == 'saida')\
     .group_by(Category.name).all()
    
    # 3. Últimas 5 Transações (Para a lista central)
    recent_transactions = db.query(Transaction).filter(
        Transaction.room_id == room_id
    ).order_by(Transaction.date.desc()).limit(5).all()

    # 4. Dados para o Gráfico de Linha (Fluxo Financeiro)
    # Por enquanto, enviamos dados estáticos formatados, mas a estrutura já permite o front ler
    chart_labels = ["01/08", "05/08", "10/08", "15/08", "20/08", "25/08", "31/08"]
    chart_income = [1800, 2000, 1900, 2500, 2800, 3500, 3850]
    chart_expenses = [1200, 1500, 1400, 1800, 2000, 2200, 2600]

    return {
        "summary": {
            "total_balance": income - expenses,
            "monthly_income": income,
            "monthly_expenses": expenses,
            "debt_summary": "Tudo em dia"
        },
        "categories": [{"name": c[0], "value": c[1]} for c in categories_data],
        "recent": [
            {
                "description": t.description,
                "amount": t.amount,
                "type": t.type,
                "date": t.date.strftime("%d/%m/%Y"),
                "category": t.category.name if t.category else "Outros"
            } for t in recent_transactions
        ],
        "chart_data": {
            "labels": chart_labels,
            "income": chart_income,
            "expenses": chart_expenses
        }
    }


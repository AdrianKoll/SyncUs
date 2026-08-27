import calendar
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.enums import PaidBy, SplitType, TransactionType
from ..models.models import Category, Transaction, User
from ..schemas.transaction import (
    Category as CategorySchema,
    CategoryCreate,
    Transaction as TransactionSchema,
    TransactionCreate,
    TransactionUpdate,
)
from ..services.room_service import ensure_default_categories


router = APIRouter()


def _room_required(current_user: User):
    if not current_user.room_id:
        raise HTTPException(
            status_code=400,
            detail="Você precisa estar conectado a uma sala para acessar os dados financeiros",
        )
    return current_user.room_id


def _category_for_room(db: Session, room_id: int, category_id: Optional[int]):
    if category_id is None:
        return (
            db.query(Category)
            .filter(Category.room_id == room_id, func.lower(Category.name) == "outros")
            .first()
        )

    category = db.query(Category).filter(
        Category.id == category_id,
        or_(Category.room_id == room_id, Category.room_id.is_(None)),
    ).first()
    if not category:
        raise HTTPException(status_code=400, detail="Categoria inválida para esta sala")
    return category


def _apply_transaction_filters(
    query,
    room_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_type: Optional[TransactionType] = None,
    category_id: Optional[int] = None,
):
    query = query.filter(Transaction.room_id == room_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date < end_date)
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    return query


def _period_bounds(year: Optional[int], month: Optional[int]):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    selected_year = year or now.year
    selected_month = month or now.month
    if selected_month < 1 or selected_month > 12:
        raise HTTPException(status_code=400, detail="Mês inválido")
    if selected_year < 2000 or selected_year > 2100:
        raise HTTPException(status_code=400, detail="Ano inválido")

    start = datetime(selected_year, selected_month, 1)
    if selected_month == 12:
        end = datetime(selected_year + 1, 1, 1)
    else:
        end = datetime(selected_year, selected_month + 1, 1)
    return selected_year, selected_month, start, end


MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0.00")


def _as_money(value: Any, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} inválido") from exc

    if not amount.is_finite():
        raise HTTPException(status_code=400, detail=f"{field_name} inválido")
    quantized = amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    if quantized != amount:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} deve possuir no máximo duas casas decimais",
        )
    return quantized


def _half_split(amount: Decimal) -> tuple[Decimal, Decimal]:
    first = (amount / 2).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    return first, amount - first


def _normalize_custom_split_data(
    amount: Decimal,
    split_type: SplitType | str,
    raw_data: Optional[str | dict[str, Any]],
):
    split_value = getattr(split_type, "value", split_type)
    if split_value != SplitType.CUSTOM.value:
        return None
    if not raw_data:
        raise HTTPException(
            status_code=400,
            detail="Informe quanto cada pessoa pagou na divisão personalizada",
        )

    try:
        data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        if not isinstance(data, dict):
            raise ValueError("rateio deve ser um objeto")
        eu = _as_money(
            data.get("eu", data.get("user1", data.get("current_user", ZERO))),
            "Valor de eu",
        )
        parceira = _as_money(
            data.get("parceira", data.get("partner", data.get("user2", ZERO))),
            "Valor da parceira",
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Valores da divisão personalizada inválidos",
        ) from exc

    if eu < ZERO or parceira < ZERO or eu + parceira != _as_money(amount, "Valor"):
        raise HTTPException(
            status_code=400,
            detail="A soma dos valores personalizados deve ser igual ao valor do lançamento",
        )
    return json.dumps({"eu": f"{eu:.2f}", "parceira": f"{parceira:.2f}"})


def _payment_values(transaction: Transaction):
    amount = _as_money(transaction.amount, "Valor")
    split_type = getattr(transaction.split_type, "value", transaction.split_type)
    paid_by = getattr(transaction.paid_by, "value", transaction.paid_by)
    if split_type == SplitType.CUSTOM.value and transaction.custom_split_data:
        try:
            data = json.loads(transaction.custom_split_data)
            return (
                _as_money(data.get("eu", data.get("user1", ZERO)), "Rateio de eu"),
                _as_money(data.get("parceira", data.get("user2", ZERO)), "Rateio da parceira"),
            )
        except (TypeError, ValueError, json.JSONDecodeError, HTTPException):
            pass
    if paid_by == PaidBy.PARCEIRA.value:
        return ZERO, amount
    if paid_by == PaidBy.AMBOS.value:
        return _half_split(amount)
    return amount, ZERO


def _responsibility_values(transaction: Transaction):
    amount = _as_money(transaction.amount, "Valor")
    split_type = getattr(transaction.split_type, "value", transaction.split_type)
    if split_type == SplitType.FULL_USER1.value:
        return amount, ZERO
    if split_type == SplitType.FULL_USER2.value:
        return ZERO, amount
    return _half_split(amount)


def _serialize_transaction(transaction: Transaction):
    return {
        "id": transaction.id,
        "amount": float(transaction.amount),
        "description": transaction.description,
        "category_id": transaction.category_id,
        "type": transaction.type,
        "date": transaction.date.isoformat(),
        "paid_by": transaction.paid_by,
        "split_type": transaction.split_type,
        "custom_split_data": transaction.custom_split_data,
        "room_id": transaction.room_id,
        "user_id": transaction.user_id,
        "category": (
            {
                "id": transaction.category.id,
                "name": transaction.category.name,
                "room_id": transaction.category.room_id,
            }
            if transaction.category
            else None
        ),
    }


@router.get("/categories", response_model=List[CategorySchema])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    ensure_default_categories(db, room_id)
    db.commit()
    return db.query(Category).filter(Category.room_id == room_id).order_by(Category.name.asc()).all()


@router.post("/categories", response_model=CategorySchema, status_code=201)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    name = category_in.name.strip()
    existing = db.query(Category).filter(
        Category.room_id == room_id,
        func.lower(Category.name) == name.lower(),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Categoria já cadastrada")

    category = Category(name=name, room_id=room_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.room_id == room_id,
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    db.query(Transaction).filter(Transaction.category_id == category.id).update(
        {Transaction.category_id: None}, synchronize_session=False
    )
    db.delete(category)
    db.commit()
    return {"message": "Categoria excluída com sucesso"}


@router.post("/", response_model=TransactionSchema)
def create_transaction(
    transaction_in: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    ensure_default_categories(db, room_id)
    category = _category_for_room(db, room_id, transaction_in.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Não foi possível determinar a categoria")

    data = transaction_in.model_dump()
    data["category_id"] = category.id
    data["custom_split_data"] = _normalize_custom_split_data(
        data["amount"], data["split_type"], data.get("custom_split_data")
    )
    db_transaction = Transaction(**data, room_id=room_id, user_id=current_user.id)
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


@router.get("/", response_model=List[TransactionSchema])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    type: Optional[TransactionType] = None,
    category_id: Optional[int] = None,
):
    if not current_user.room_id:
        return []

    query = _apply_transaction_filters(
        db.query(Transaction),
        current_user.room_id,
        start_date,
        end_date,
        type,
        category_id,
    )
    return query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(skip).limit(limit).all()


@router.get("/all", response_model=List[TransactionSchema])
def get_all_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.room_id:
        return []
    return db.query(Transaction).filter(
        Transaction.room_id == current_user.room_id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).all()


@router.put("/{transaction_id}", response_model=TransactionSchema)
def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.room_id == room_id,
    ).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado ou acesso negado")

    update_data = transaction_update.model_dump(exclude_unset=True)
    if "split_type" in update_data or "custom_split_data" in update_data or "amount" in update_data:
        next_amount = update_data.get("amount", db_transaction.amount)
        next_split_type = update_data.get("split_type", db_transaction.split_type)
        next_custom_data = update_data.get("custom_split_data", db_transaction.custom_split_data)
        update_data["custom_split_data"] = _normalize_custom_split_data(
            next_amount, next_split_type, next_custom_data
        )
    if "category_id" in update_data:
        category = _category_for_room(db, room_id, update_data["category_id"])
        update_data["category_id"] = category.id if category else None

    for key, value in update_data.items():
        setattr(db_transaction, key, value)

    db.commit()
    db.refresh(db_transaction)
    return db_transaction


@router.delete("/all")
def delete_all_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    deleted = db.query(Transaction).filter(Transaction.room_id == room_id).delete(
        synchronize_session=False
    )
    db.commit()
    return {"message": "Todos os lançamentos foram excluídos", "deleted": deleted}


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room_id = _room_required(current_user)
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.room_id == room_id,
    ).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado ou acesso negado")

    db.delete(db_transaction)
    db.commit()
    return {"message": "Lançamento excluído com sucesso"}


@router.get("/dashboard", response_model=dict)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    if not current_user.room_id:
        return {
            "period": None,
            "summary": {
                "total_balance": 0,
                "monthly_income": 0,
                "monthly_expenses": 0,
                "monthly_balance": 0,
                "debt_summary": "Desconectado",
            },
            "categories": [],
            "recent": [],
            "chart_data": {"labels": [], "income": [], "expenses": []},
        }

    selected_year, selected_month, period_start, period_end = _period_bounds(year, month)
    room_id = current_user.room_id
    period_query = _apply_transaction_filters(
        db.query(Transaction), room_id, period_start, period_end
    )
    income = period_query.filter(Transaction.type == "entrada").with_entities(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).scalar() or 0
    expenses = period_query.filter(Transaction.type == "saida").with_entities(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).scalar() or 0

    categories_data = db.query(
        Category.name,
        func.coalesce(func.sum(Transaction.amount), 0).label("total"),
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.room_id == room_id,
        Transaction.type == "saida",
        Transaction.date >= period_start,
        Transaction.date < period_end,
    ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).all()

    recent_transactions = period_query.order_by(
        Transaction.date.desc(), Transaction.id.desc()
    ).limit(5).all()

    period_transactions = period_query.all()
    couple_balance = ZERO
    for transaction in period_transactions:
        if transaction.type != "saida":
            continue
        paid_eu, _ = _payment_values(transaction)
        responsibility_eu, _ = _responsibility_values(transaction)
        couple_balance += paid_eu - responsibility_eu

    days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    chart_income = [ZERO] * days_in_month
    chart_expenses = [ZERO] * days_in_month
    for transaction in period_transactions:
        index = transaction.date.day - 1
        if transaction.type == "entrada":
            chart_income[index] += _as_money(transaction.amount, "Valor")
        elif transaction.type == "saida":
            chart_expenses[index] += _as_money(transaction.amount, "Valor")

    return {
        "period": {"year": selected_year, "month": selected_month},
        "summary": {
            "total_balance": float(income - expenses),
            "monthly_income": float(income),
            "monthly_expenses": float(expenses),
            "monthly_balance": float(income - expenses),
            "debt_summary": "Tudo em dia" if couple_balance == 0 else "Ajuste pendente",
        },
        "couple_balance": {
            "amount": float(abs(couple_balance)),
            "direction": "partner_owes_current" if couple_balance > 0 else "current_owes_partner" if couple_balance < 0 else "settled",
        },
        "categories": [
                {"name": name, "value": float(total or ZERO)}

            for name, total in categories_data
        ],
        "recent": [
            {
                "id": transaction.id,
                "description": transaction.description,
                "amount": float(_as_money(transaction.amount, "Valor")),
                "type": transaction.type,
                "date": transaction.date.strftime("%d/%m/%Y"),
                "category": transaction.category.name if transaction.category else "Outros",
            }
            for transaction in recent_transactions
        ],
        "chart_data": {
            "labels": [
                f"{day:02d}/{selected_month:02d}" for day in range(1, days_in_month + 1)
            ],
            "income": [float(value) for value in chart_income],
            "expenses": [float(value) for value in chart_expenses],
        },
    }

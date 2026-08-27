from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError


def _transaction_payload(**overrides):
    payload = {
        "amount": "10.25",
        "description": "Teste de contrato",
        "category_id": None,
        "type": "saida",
        "date": "2026-08-27T12:00:00",
        "paid_by": "eu",
        "split_type": "50/50",
        "custom_split_data": None,
    }
    payload.update(overrides)
    return payload


def test_transaction_contract_uses_decimal_and_canonical_enums():
    from app.models.enums import PaidBy, SplitType, TransactionType
    from app.schemas.transaction import TransactionCreate

    transaction = TransactionCreate(**_transaction_payload())

    assert transaction.amount == Decimal("10.25")
    assert transaction.type is TransactionType.SAIDA
    assert transaction.paid_by is PaidBy.EU
    assert transaction.split_type is SplitType.HALF


def test_transaction_contract_rejects_more_than_two_decimal_places():
    from app.schemas.transaction import TransactionCreate, TransactionUpdate

    with pytest.raises(ValidationError):
        TransactionCreate(**_transaction_payload(amount="10.257"))

    with pytest.raises(ValidationError):
        TransactionUpdate(amount="10.257")


def test_transaction_contract_rejects_negative_amount():
    from app.schemas.transaction import TransactionCreate

    with pytest.raises(ValidationError):
        TransactionCreate(**_transaction_payload(amount="-0.01"))


def test_transaction_contract_rejects_unknown_enum_values():
    from app.schemas.transaction import TransactionCreate

    for field, value in (
        ("type", "transferencia"),
        ("paid_by", "qualquer_pessoa"),
        ("split_type", "90/10"),
    ):
        with pytest.raises(ValidationError):
            TransactionCreate(**_transaction_payload(**{field: value}))


def test_database_enforces_money_and_enum_constraints():
    from app.core.database import Base
    from app.models.models import Category, Room, Transaction, User
    from sqlalchemy import create_engine
    from sqlalchemy.exc import IntegrityError, StatementError
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        user = User(
            name="Contract User",
            email="contract-user@example.com",
            hashed_password="hash",
        )
        room = Room()
        category = Category(name="Outros")
        session.add_all([user, room, category])
        session.commit()

        session.add(
            Transaction(
                amount=Decimal("1.00"),
                description="válida",
                category_id=category.id,
                type="saida",
                date=datetime(2026, 8, 27, 12, 0, 0),
                paid_by="eu",
                split_type="50/50",
                room_id=room.id,
                user_id=user.id,
            )
        )
        session.commit()

        session.add(
            Transaction(
                amount=Decimal("1.00"),
                description="tipo inválido",
                category_id=category.id,
                type="transferencia",
                date=datetime(2026, 8, 27, 12, 0, 0),
                paid_by="eu",
                split_type="50/50",
                room_id=room.id,
                user_id=user.id,
            )
        )
        with pytest.raises((StatementError, LookupError, IntegrityError)):
            session.commit()
        session.rollback()

        session.add(
            Transaction(
                amount=Decimal("-0.01"),
                description="valor negativo",
                category_id=category.id,
                type="saida",
                date=datetime(2026, 8, 27, 12, 0, 0),
                paid_by="eu",
                split_type="50/50",
                room_id=room.id,
                user_id=user.id,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()
        engine.dispose()

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from ..models.enums import PaidBy, SplitType, TransactionType


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    room_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    amount: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )
    description: str = Field(min_length=1, max_length=255)
    category_id: Optional[int] = None
    type: TransactionType
    date: datetime
    paid_by: PaidBy
    split_type: SplitType
    custom_split_data: Optional[Union[str, dict[str, Any]]] = None

    @field_serializer("amount", when_used="json")
    def serialize_amount(self, value: Decimal) -> float:
        return float(value)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )
    description: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category_id: Optional[int] = None
    type: Optional[TransactionType] = None
    date: Optional[datetime] = None
    paid_by: Optional[PaidBy] = None
    split_type: Optional[SplitType] = None
    custom_split_data: Optional[Union[str, dict[str, Any]]] = None


class Transaction(TransactionBase):
    id: int
    room_id: int
    user_id: int
    category: Optional[Category] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionListParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    type: Optional[TransactionType] = None
    category_id: Optional[int] = None


class DashboardSummary(BaseModel):
    total_balance: Decimal
    monthly_income: Decimal
    monthly_expenses: Decimal
    monthly_balance: Decimal
    debt_summary: str


class ReportPayerTotals(BaseModel):
    eu: Decimal = Decimal("0.00")
    parceira: Decimal = Decimal("0.00")
    ambos: Decimal = Decimal("0.00")


class ReportCategory(BaseModel):
    name: str
    value: Decimal


class ReportAggregates(BaseModel):
    transaction_count: int
    categories: list[ReportCategory]
    payer_totals: ReportPayerTotals
    daily: dict[str, dict[str, Decimal]]


class ReportTransaction(BaseModel):
    id: int
    amount: str
    description: str
    category_id: Optional[int] = None
    type: TransactionType
    date: datetime
    paid_by: PaidBy
    split_type: SplitType
    custom_split_data: Optional[Union[str, dict[str, Any]]] = None
    room_id: int
    user_id: int
    category: Optional[Category] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionReport(BaseModel):
    period: dict[str, int]
    summary: DashboardSummary
    aggregates: ReportAggregates
    transactions: list[ReportTransaction]

    model_config = ConfigDict(from_attributes=True)

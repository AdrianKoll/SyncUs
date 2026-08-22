from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    room_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    amount: float = Field(ge=0)
    description: str = Field(min_length=1, max_length=255)
    category_id: Optional[int] = None
    type: str
    date: datetime
    paid_by: str
    split_type: str
    custom_split_data: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category_id: Optional[int] = None
    type: Optional[str] = None
    date: Optional[datetime] = None
    paid_by: Optional[str] = None
    split_type: Optional[str] = None
    custom_split_data: Optional[str] = None


class Transaction(TransactionBase):
    id: int
    room_id: int
    user_id: int
    category: Optional[Category] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionListParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    type: Optional[str] = None
    category_id: Optional[int] = None


class DashboardSummary(BaseModel):
    total_balance: float
    monthly_income: float
    monthly_expenses: float
    monthly_balance: float
    debt_summary: str

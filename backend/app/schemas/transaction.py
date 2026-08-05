from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    room_id: Optional[int] = None

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    amount: float
    description: str
    category_id: int
    type: str  # 'entrada' or 'saida'
    date: datetime
    paid_by: str
    split_type: str
    custom_split_data: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    room_id: int
    user_id: int
    category: Category

    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    total_balance: float
    monthly_income: float
    monthly_expenses: float
    monthly_balance: float
    debt_summary: str

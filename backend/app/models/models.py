from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base  # ✅ CORRIGIDO O CAMINHO DA IMPORTAÇÃO
from app.models.enums import PaidBy, SplitType, TransactionType
import datetime


TransactionTypeEnum = SAEnum(
    TransactionType,
    name="transaction_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum: [member.value for member in enum],
)
PaidByEnum = SAEnum(
    PaidBy,
    name="paid_by",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum: [member.value for member in enum],
)
SplitTypeEnum = SAEnum(
    SplitType,
    name="split_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda enum: [member.value for member in enum],
)


def utcnow_naive():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Token de conexão do usuário (gerado para que outros se conectem a ele)
    connection_token = Column(String, unique=True, index=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # ID da sala compartilhada
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    
    room = relationship("Room", back_populates="users", foreign_keys=[room_id])


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    users = relationship("User", back_populates="room", foreign_keys=[User.room_id])
    transactions = relationship("Transaction", back_populates="room")
    categories = relationship("Category", back_populates="room")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_transactions_amount_non_negative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    type = Column(TransactionTypeEnum, nullable=False)
    date = Column(DateTime, nullable=False)
    paid_by = Column(PaidByEnum, nullable=False)
    split_type = Column(SplitTypeEnum, nullable=False)
    custom_split_data = Column(String, nullable=True) # JSON string para divisões personalizadas
    
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id")) # Quem registrou
    
    room = relationship("Room", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True) # NULL para categorias padrão
    
    room = relationship("Room", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")


# ==============================================
# ✅ NOVOS MODELS — Convites, Conexões e Notificações
# ==============================================

class CoupleInvite(Base):
    """Pedido de vínculo pendente de aprovação"""
    __tablename__ = "couple_invites"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_used = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending / accepted / rejected
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class CoupleConnection(Base):
    """Vínculo ativo e confirmado do casal."""
    __tablename__ = "couple_connections"
    __table_args__ = (
        CheckConstraint(
            "user1_id < user2_id",
            name="ck_couple_connections_ordered_users",
        ),
        # O par é sempre gravado em ordem crescente. Assim, os índices
        # separados impedem que um usuário apareça em qualquer posição de
        # mais de uma conexão ativa.
        Index(
            "uq_active_couple_user1",
            "user1_id",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
        Index(
            "uq_active_couple_user2",
            "user2_id",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    connected_at = Column(DateTime, default=utcnow_naive)
    disconnected_at = Column(DateTime, nullable=True)

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    members = relationship(
        "CoupleConnectionMember",
        back_populates="connection",
        cascade="all, delete-orphan",
    )


class CoupleConnectionMember(Base):
    """Membro ativo de uma conexão; existe somente enquanto o vínculo está ativo."""
    __tablename__ = "couple_connection_members"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "user_id",
            name="uq_couple_connection_member_pair",
        ),
        Index(
            "uq_active_couple_member_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(
        Integer,
        ForeignKey("couple_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)

    connection = relationship("CoupleConnection", back_populates="members")
    user = relationship("User")


class Notification(Base):
    """Notificações do sininho"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # invite_income / invite_accepted / invite_rejected / disconnect
    related_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow_naive)

    user = relationship("User")
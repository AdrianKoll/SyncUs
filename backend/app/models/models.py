from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base  # ✅ CORRIGIDO O CAMINHO DA IMPORTAÇÃO
import datetime


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
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    type = Column(String, nullable=False)  # 'entrada' ou 'saida'
    date = Column(DateTime, nullable=False)
    paid_by = Column(String, nullable=False)  # 'user1', 'user2', 'both'
    split_type = Column(String, nullable=False)  # '50/50', '100_user1', '100_user2', 'custom'
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class CoupleConnection(Base):
    """Vínculo ativo e confirmado do casal"""
    __tablename__ = "couple_connections"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.datetime.utcnow)
    disconnected_at = Column(DateTime, nullable=True)

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])


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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.models.models import User, CoupleInvite, CoupleConnection, Notification
from pydantic import BaseModel

# Schemas locais (sem precisar criar arquivo separado agora)
class InviteCreate(BaseModel):
    token: str

class PartnerResponse(BaseModel):
    id: int
    nome: str
    email: str
    conectado_em: str

class ConnectionResponse(BaseModel):
    conectado: bool
    parceiro: PartnerResponse | None = None

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

router = APIRouter(prefix="/api/couple", tags=["Vínculo de Casal"])


# 📤 ENVIAR PEDIDO DE VÍNCULO (cola o token e pede conexão)
@router.post("/invite/send", status_code=201)
def send_invite(
    invite_data: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Busca quem pertence o token colado
    target_user = db.query(User).filter(User.connection_token == invite_data.token).first()
    if not target_user:
        raise HTTPException(404, "Token inválido, expirado ou já utilizado")

    if target_user.id == current_user.id:
        raise HTTPException(400, "Não pode se conectar com você mesmo")

    # 2. Verifica se já estão conectados
    existing = db.query(CoupleConnection).filter(
        ((CoupleConnection.user1_id == current_user.id) & (CoupleConnection.user2_id == target_user.id)) |
        ((CoupleConnection.user1_id == target_user.id) & (CoupleConnection.user2_id == current_user.id)),
        CoupleConnection.is_active == True
    ).first()
    if existing:
        raise HTTPException(400, "Vocês já estão conectados!")

    # 3. Cria convite pendente
    new_invite = CoupleInvite(
        sender_id=current_user.id,
        receiver_id=target_user.id,
        token_used=invite_data.token
    )
    db.add(new_invite)

    # 4. Cria NOTIFICAÇÃO para o dono do token
    db.add(Notification(
        user_id=target_user.id,
        title="📩 Alguém quer se conectar com você!",
        message=f"{current_user.name} quer ser seu parceiro. E-mail: {current_user.email}",
        type="invite_income",
        related_id=new_invite.id
    ))

    db.commit()
    return {
        "sucesso": True,
        "mensagem": f"Pedido enviado para {target_user.name}! Aguardando aprovação.",
        "destinatario": target_user.name
    }


# ✅ ACEITAR PEDIDO DE VÍNCULO
@router.post("/invite/{invite_id}/accept")
def accept_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invite = db.query(CoupleInvite).filter_by(
        id=invite_id,
        receiver_id=current_user.id,
        status="pending"
    ).first()

    if not invite:
        raise HTTPException(404, "Convite não encontrado ou já respondido")

    # Marca convite como aceito
    invite.status = "accepted"

    # CRIA CONEXÃO OFICIAL
    connection = CoupleConnection(
        user1_id=invite.sender_id,
        user2_id=invite.receiver_id
    )
    db.add(connection)

    # INVALIDA o token usado (não serve mais)
    sender = db.query(User).get(invite.sender_id)
    sender.connection_token = None

    # NOTIFICA quem pediu que foi aceito
    db.add(Notification(
        user_id=invite.sender_id,
        title="✅ Convite ACEITO!",
        message=f"{current_user.name} aceitou seu vínculo! Vocês já estão conectados.",
        type="invite_accepted"
    ))

    db.commit()
    return {"sucesso": True, "mensagem": "Parabéns! Vínculo aprovado. Vocês já estão conectados."}


# ❌ RECUSAR PEDIDO
@router.post("/invite/{invite_id}/reject")
def reject_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invite = db.query(CoupleInvite).filter_by(
        id=invite_id,
        receiver_id=current_user.id,
        status="pending"
    ).first()

    if not invite:
        raise HTTPException(404, "Convite não encontrado")

    invite.status = "rejected"

    # Avisa quem pediu que foi recusado
    db.add(Notification(
        user_id=invite.sender_id,
        title="❌ Convite RECUSADO",
        message=f"{current_user.name} recusou seu pedido de vínculo.",
        type="invite_rejected"
    ))

    db.commit()
    return {"sucesso": True, "mensagem": "Convite recusado."}


# 🔍 VER DADOS DO PARCEIRO CONECTADO
@router.get("/partner", response_model=ConnectionResponse)
def get_partner(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conn = db.query(CoupleConnection).filter(
        ((CoupleConnection.user1_id == current_user.id) | (CoupleConnection.user2_id == current_user.id)),
        CoupleConnection.is_active == True
    ).first()

    if not conn:
        return {"conectado": False, "parceiro": None}

    # Descobre qual é o outro usuário
    partner_id = conn.user2_id if conn.user1_id == current_user.id else conn.user1_id
    partner = db.query(User).get(partner_id)

    return {
        "conectado": True,
        "parceiro": {
            "id": partner.id,
            "nome": partner.name,
            "email": partner.email,
            "conectado_em": conn.connected_at.strftime("%d/%m/%Y às %H:%M")
        }
    }


# ❌ DESVINCULAR PARCEIRO
@router.post("/disconnect")
def disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conn = db.query(CoupleConnection).filter(
        ((CoupleConnection.user1_id == current_user.id) | (CoupleConnection.user2_id == current_user.id)),
        CoupleConnection.is_active == True
    ).first()

    if not conn:
        raise HTTPException(400, "Nenhuma conexão ativa para desfazer")

    conn.is_active = False
    conn.disconnected_at = datetime.utcnow()

    # Avisa o parceiro que foi desvinculado
    other_id = conn.user2_id if conn.user1_id == current_user.id else conn.user1_id
    db.add(Notification(
        user_id=other_id,
        title="⚠️ Vínculo ENCERRADO",
        message=f"{current_user.name} desfez a conexão com você.",
        type="disconnect"
    ))

    db.commit()
    return {"sucesso": True, "mensagem": "Vínculo desfeito com sucesso."}


# 📬 MINHAS NOTIFICAÇÕES (para o sininho)
@router.get("/notifications", response_model=List[NotificationResponse])
def my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Notification)\
        .filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(15)\
        .all()
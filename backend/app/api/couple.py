from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.deps import get_db, get_current_user
from app.models.models import User, CoupleInvite, CoupleConnection, Notification
from pydantic import BaseModel

# Schemas locais
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
    related_id: int | None = None

    class Config:
        from_attributes = True

router = APIRouter(prefix="/api/couple", tags=["Vínculo de Casal"])

# 📤 ENVIAR PEDIDO DE VÍNCULO
@router.post("/invite/send", status_code=201)
def send_invite(
    invite_data: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Busca quem pertence o token
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
    
    # 3. Cancela convites pendentes antigos
    convites_antigos = db.query(CoupleInvite).filter(
        ((CoupleInvite.sender_id == current_user.id) & (CoupleInvite.receiver_id == target_user.id)) |
        ((CoupleInvite.sender_id == target_user.id) & (CoupleInvite.receiver_id == current_user.id)),
        CoupleInvite.status == "pending"
    ).all()
    for convite in convites_antigos:
        convite.status = "rejected"
        db.query(Notification).filter(
            Notification.type == "invite_income",
            Notification.related_id == convite.id
        ).delete(synchronize_session=False)
    
    # 4. Apaga notificações antigas
    db.query(Notification).filter(
        Notification.user_id.in_([current_user.id, target_user.id]),
        Notification.type.in_(["invite_accepted", "invite_rejected", "disconnect"])
    ).delete(synchronize_session=False)
    
    # 5. Cria convite novo
    new_invite = CoupleInvite(
        sender_id=current_user.id,
        receiver_id=target_user.id,
        token_used=invite_data.token
    )
    db.add(new_invite)
    db.flush()
    
    # 6. Cria notificação nova
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
    
    invite.status = "accepted"
    
    connection = CoupleConnection(
        user1_id=invite.sender_id,
        user2_id=invite.receiver_id
    )
    db.add(connection)
    
    sender = db.query(User).get(invite.sender_id)
    sender.connection_token = None
    
    notif = db.query(Notification).filter_by(
        user_id=current_user.id,
        type="invite_income",
        related_id=invite_id
    ).first()
    if notif:
        notif.is_read = True
    
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
    
    notif = db.query(Notification).filter_by(
        user_id=current_user.id,
        type="invite_income",
        related_id=invite_id
    ).first()
    if notif:
        notif.is_read = True
    
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
    
    partner_id = conn.user2_id if conn.user1_id == current_user.id else conn.user1_id
    partner = db.query(User).get(partner_id)
    
    return {
        "conectado": True,
        "parceiro": {
            "id": partner.id,
            "nome": partner.name,
            "email": partner.email,
            "conectado_em": conn.connected_at.strftime("%d/%m/%Y às %H:%M") if conn.connected_at else ""
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
    
    other_id = conn.user2_id if conn.user1_id == current_user.id else conn.user1_id
    
    db.query(Notification).filter(
        Notification.user_id.in_([current_user.id, other_id]),
        Notification.type.in_(["invite_income", "invite_accepted"])
    ).update({"is_read": True}, synchronize_session=False)
    
    db.add(Notification(
        user_id=other_id,
        title="⚠️ Vínculo ENCERRADO",
        message=f"{current_user.name} desfez a conexão com você.",
        type="disconnect"
    ))
    db.commit()
    
    return {"sucesso": True, "mensagem": "Vínculo desfeito com sucesso."}

# 📬 MINHAS NOTIFICAÇÕES
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

# 📭 MARCAR NOTIFICAÇÃO COMO LIDA
@router.put("/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter_by(
        id=notif_id,
        user_id=current_user.id
    ).first()
    if not notif:
        raise HTTPException(404, "Notificação não encontrada")
    notif.is_read = True
    db.commit()
    return {"sucesso": True, "mensagem": "Notificação marcada como lida"}

# 📭 MARCAR TODAS COMO LIDAS
@router.put("/notifications/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Notification).filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({"is_read": True})
    db.commit()
    return {"sucesso": True, "mensagem": "Todas marcadas como lidas"}

# 🗑️ APAGAR NOTIFICAÇÃO INDIVIDUAL
@router.delete("/notifications/{notif_id}")
def delete_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter_by(
        id=notif_id,
        user_id=current_user.id
    ).first()
    if not notif:
        raise HTTPException(404, "Notificação não encontrada")
    db.delete(notif)
    db.commit()
    return {"sucesso": True, "mensagem": "Notificação apagada"}

# 🗑️ APAGAR TODAS NOTIFICAÇÕES LIDAS
@router.delete("/notifications/clear/read")
def clear_read_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deletadas = db.query(Notification).filter_by(
        user_id=current_user.id,
        is_read=True
    ).delete(synchronize_session=False)
    db.commit()
    return {"sucesso": True, "mensagem": f"{deletadas} notificações apagadas"}
import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.models import User, Room, Category
from ..repositories import user_repository

def generate_token():
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(6))
    part2 = ''.join(secrets.choice(chars) for _ in range(4))
    return f"CASAL-{part1}-{part2}"

def refresh_user_token(db: Session, user: User):
    user.connection_token = generate_token()
    user.token_expires_at = datetime.utcnow() + timedelta(days=7)
    db.commit()
    db.refresh(user)
    return user

def connect_users(db: Session, current_user: User, partner_token: str):
    partner = user_repository.get_user_by_token(db, partner_token)
    
    if not partner:
        return None, "Token inválido"
    
    if partner.token_expires_at < datetime.utcnow():
        return None, "Token expirado"
        
    if partner.id == current_user.id:
        return None, "Você não pode se conectar a si mesmo"

    # Criar sala se nenhum tiver
    if not partner.room_id and not current_user.room_id:
        new_room = Room()
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        partner.room_id = new_room.id
        current_user.room_id = new_room.id
    elif partner.room_id and not current_user.room_id:
        current_user.room_id = partner.room_id
    elif not partner.room_id and current_user.room_id:
        partner.room_id = current_user.room_id
    else:
        return None, "Ambos já estão em salas diferentes"

    db.commit()
    return True, "Conectado com sucesso"

def disconnect_room(db: Session, user: User):
    user.room_id = None
    db.commit()
    return True

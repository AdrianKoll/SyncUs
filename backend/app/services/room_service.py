import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.models import Category, Room, User
from ..repositories import user_repository


DEFAULT_CATEGORY_NAMES = (
    "Moradia",
    "Alimentação",
    "Transporte",
    "Lazer",
    "Salário",
    "Outros",
)


def generate_token():
    chars = string.ascii_uppercase + string.digits
    part1 = "".join(secrets.choice(chars) for _ in range(6))
    part2 = "".join(secrets.choice(chars) for _ in range(4))
    return f"CASAL-{part1}-{part2}"


def refresh_user_token(db: Session, user: User):
    token = generate_token()
    while user_repository.get_user_by_token(db, token):
        token = generate_token()

    user.connection_token = token
    user.token_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    db.commit()
    db.refresh(user)
    return user


def ensure_default_categories(db: Session, room_id: int):
    existing = {
        name.lower()
        for (name,) in db.query(Category.name)
        .filter(Category.room_id == room_id)
        .all()
    }

    for name in DEFAULT_CATEGORY_NAMES:
        if name.lower() not in existing:
            db.add(Category(name=name, room_id=room_id))

    db.flush()


def ensure_room_for_users(db: Session, first_user: User, second_user: User):
    if first_user.id == second_user.id:
        raise ValueError("Não é possível criar uma sala para o mesmo usuário")

    if first_user.room_id and second_user.room_id and first_user.room_id != second_user.room_id:
        raise ValueError("Ambos já estão em salas diferentes")

    room_id = first_user.room_id or second_user.room_id
    if not room_id:
        room = Room()
        db.add(room)
        db.flush()
        room_id = room.id

    first_user.room_id = room_id
    second_user.room_id = room_id
    ensure_default_categories(db, room_id)
    return room_id


def connect_users(db: Session, current_user: User, partner_token: str):
    partner = user_repository.get_user_by_token(db, partner_token)

    if not partner:
        return None, "Token inválido"

    if not partner.token_expires_at or partner.token_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return None, "Token expirado"

    if partner.id == current_user.id:
        return None, "Você não pode se conectar a si mesmo"

    try:
        ensure_room_for_users(db, current_user, partner)
    except ValueError as exc:
        return None, str(exc)

    db.commit()
    return True, "Conectado com sucesso"


def disconnect_room(db: Session, user: User):
    user.room_id = None
    db.commit()
    return True

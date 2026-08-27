import secrets
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.models import (
    Category,
    CoupleConnection,
    CoupleConnectionMember,
    Room,
    User,
)
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


def ensure_active_connection_members(db: Session):
    """Sincroniza conexões ativas legadas com a tabela de membros únicos."""
    active_connections = db.query(CoupleConnection).filter(
        CoupleConnection.is_active.is_(True)
    ).order_by(CoupleConnection.id).all()

    for connection in active_connections:
        if connection.user1_id == connection.user2_id:
            raise ValueError(
                "Existe um vínculo ativo inválido com o mesmo usuário nas duas posições"
            )
        if connection.user1_id > connection.user2_id:
            connection.user1_id, connection.user2_id = (
                connection.user2_id,
                connection.user1_id,
            )

        active_member_ids = {
            member.user_id
            for member in connection.members
            if member.is_active
        }
        expected_member_ids = {connection.user1_id, connection.user2_id}
        if active_member_ids - expected_member_ids:
            raise ValueError(
                "Existe um membro inválido em uma conexão ativa"
            )

        for user_id in expected_member_ids - active_member_ids:
            db.add(
                CoupleConnectionMember(
                    connection_id=connection.id,
                    user_id=user_id,
                    is_active=True,
                )
            )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Existem usuários em mais de um vínculo ativo; resolva os dados legados antes de iniciar"
        ) from exc


def get_active_connection_for_user(db: Session, user_id: int):
    """Retorna o único vínculo ativo permitido para o usuário, se existir."""
    return db.query(CoupleConnection).filter(
        (
            (CoupleConnection.user1_id == user_id)
            | (CoupleConnection.user2_id == user_id)
        ),
        CoupleConnection.is_active.is_(True),
    ).first()


def get_active_connection_between_users(
    db: Session,
    first_user_id: int,
    second_user_id: int,
):
    return db.query(CoupleConnection).filter(
        CoupleConnection.user1_id == min(first_user_id, second_user_id),
        CoupleConnection.user2_id == max(first_user_id, second_user_id),
        CoupleConnection.is_active.is_(True),
    ).first()


def _lock_users_for_connection(
    db: Session,
    first_user: User,
    second_user: User,
) -> tuple[User, User]:
    """Bloqueia as linhas dos dois usuários durante a criação do vínculo."""
    locked_users = db.query(User).filter(
        User.id.in_([first_user.id, second_user.id])
    ).order_by(User.id).with_for_update().all()
    users_by_id = {user.id: user for user in locked_users}
    if len(users_by_id) != 2:
        raise ValueError("Usuário não encontrado")
    return users_by_id[first_user.id], users_by_id[second_user.id]


def ensure_room_for_users(db: Session, first_user: User, second_user: User):
    """Garante uma sala disponível para exatamente dois usuários."""
    if first_user.id == second_user.id:
        raise ValueError("Não é possível criar uma sala para o mesmo usuário")

    active_first = get_active_connection_for_user(db, first_user.id)
    active_second = get_active_connection_for_user(db, second_user.id)
    if active_first or active_second:
        raise ValueError("Um dos usuários já possui um vínculo ativo")

    if first_user.room_id and second_user.room_id and first_user.room_id != second_user.room_id:
        raise ValueError("Ambos já estão em salas diferentes")

    room_id = first_user.room_id or second_user.room_id
    if room_id:
        room_user_ids = {
            user_id
            for (user_id,) in db.query(User.id).filter(User.room_id == room_id).all()
        }
        allowed_user_ids = {first_user.id, second_user.id}
        if room_user_ids - allowed_user_ids or len(room_user_ids) > 2:
            raise ValueError("A sala já possui outros usuários vinculados")
    else:
        room = Room()
        db.add(room)
        db.flush()
        room_id = room.id

    first_user.room_id = room_id
    second_user.room_id = room_id
    ensure_default_categories(db, room_id)
    return room_id


def create_couple_connection(
    db: Session,
    first_user: User,
    second_user: User,
):
    """Cria uma conexão ativa ordenada e protegida contra concorrência."""
    if first_user.id == second_user.id:
        raise ValueError("Não é possível criar uma conexão com o mesmo usuário")

    existing_pair = get_active_connection_between_users(
        db, first_user.id, second_user.id
    )
    if existing_pair:
        raise ValueError("Vocês já possuem um vínculo ativo")

    first_user, second_user = _lock_users_for_connection(
        db, first_user, second_user
    )
    if get_active_connection_for_user(db, first_user.id) or get_active_connection_for_user(
        db, second_user.id
    ):
        raise ValueError("Um dos usuários já possui um vínculo ativo")

    ensure_room_for_users(db, first_user, second_user)
    user1_id, user2_id = sorted((first_user.id, second_user.id))
    connection = CoupleConnection(
        user1_id=user1_id,
        user2_id=user2_id,
        is_active=True,
    )
    db.add(connection)

    try:
        db.flush()
        db.add_all(
            [
                CoupleConnectionMember(connection_id=connection.id, user_id=user1_id),
                CoupleConnectionMember(connection_id=connection.id, user_id=user2_id),
            ]
        )
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("O vínculo já foi criado ou a sala já está ocupada") from exc

    return connection


def connect_users(db: Session, current_user: User, partner_token: str):
    partner = user_repository.get_user_by_token(db, partner_token)

    if not partner:
        return None, "Token inválido"

    if not partner.token_expires_at or partner.token_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return None, "Token expirado"

    try:
        create_couple_connection(db, current_user, partner)
        db.commit()
    except ValueError as exc:
        db.rollback()
        return None, str(exc)

    return True, "Conectado com sucesso"


def deactivate_connection(db: Session, user_id: int):
    """Desativa o vínculo do usuário e libera a sala para um novo casal."""
    connection = get_active_connection_for_user(db, user_id)
    if not connection:
        return None

    connection.is_active = False
    connection.disconnected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(CoupleConnectionMember).filter(
        CoupleConnectionMember.connection_id == connection.id,
        CoupleConnectionMember.is_active.is_(True),
    ).update({CoupleConnectionMember.is_active: False}, synchronize_session=False)
    db.query(User).filter(
        User.id.in_([connection.user1_id, connection.user2_id])
    ).update({User.room_id: None}, synchronize_session=False)
    return connection


def disconnect_room(db: Session, user: User):
    deactivate_connection(db, user.id)
    user.room_id = None
    db.commit()
    return True

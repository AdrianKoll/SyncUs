from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from ..models.models import User
from ..repositories import user_repository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_user_from_token(db: Session, token: str) -> User | None:
    """Resolve um usuário a partir de um access token JWT válido."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    return user_repository.get_user_by_email(db, email=str(subject))


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = get_user_from_token(db, token)
    if user is None:
        raise credentials_exception
    return user

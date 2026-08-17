from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.models import User
from ..schemas.user import User as UserSchema, UserUpdate
from ..repositories import user_repository
from ..services import room_service
from ..core.security import verify_password

router = APIRouter()

@router.get("/me", response_model=UserSchema)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserSchema)
def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Sempre exigir senha atual para qualquer alteração na conta
    if not user_update.current_password:
        raise HTTPException(status_code=400, detail="Senha atual é obrigatória para alterar dados da conta")
    
    if not verify_password(user_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    return user_repository.update_user(db, current_user, user_update)

@router.post("/token/refresh", response_model=UserSchema)
def refresh_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return room_service.refresh_user_token(db, current_user)

@router.post("/connect")
def connect_partner(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success, message = room_service.connect_users(db, current_user, token)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/disconnect")
def disconnect_partner(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room_service.disconnect_room(db, current_user)
    return {"message": "Desconectado com sucesso"}
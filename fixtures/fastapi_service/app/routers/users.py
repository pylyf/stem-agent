from fastapi import APIRouter

from ..models import User
from ..repositories.users import UserRepository

router = APIRouter(prefix="/users", tags=["users"])
repository = UserRepository()


@router.get("/{user_id}", response_model=User)
def read_user(user_id: int):
    return repository.get_user(user_id)


@router.get("", response_model=list[User])
def list_users():
    return repository.list_users()

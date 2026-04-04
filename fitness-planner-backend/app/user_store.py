from sqlalchemy.orm import Session

from app import crud
from app.auth import hash_password
from app.planner import normalize_gym_time
from app.schemas import UserProfileCreateRequest, UserProfileResponse, UserType


class UserAlreadyExistsError(ValueError):
    """Raised when a user profile already exists."""


class UserNotFoundError(ValueError):
    """Raised when a user profile cannot be found."""


def create_user_profile(db: Session, payload: UserProfileCreateRequest) -> UserProfileResponse:
    user_id = payload.user_id.strip()
    gym_time = payload.gym_time.strip()

    if not user_id:
        raise ValueError("user_id must not be empty.")
    if crud.get_user_by_user_id(db, user_id) is not None:
        raise UserAlreadyExistsError(f"User '{user_id}' already exists.")

    user = crud.create_user(
        db,
        user_id=user_id,
        password_hash=hash_password(payload.password),
        gym_time=normalize_gym_time(gym_time),
        goal=payload.goal,
        workout_days_per_week=payload.workout_days_per_week,
        user_type="beginner",
    )
    return UserProfileResponse.model_validate(user)


def get_user_profile(db: Session, user_id: str) -> UserProfileResponse:
    normalized_user_id = user_id.strip()
    if not normalized_user_id:
        raise ValueError("user_id must not be empty.")

    user = crud.get_user_by_user_id(db, normalized_user_id)
    if user is None:
        raise UserNotFoundError(f"User '{normalized_user_id}' was not found.")

    return UserProfileResponse.model_validate(user)


def set_user_type(db: Session, user_id: str, user_type: UserType) -> UserProfileResponse:
    user = crud.get_user_by_user_id(db, user_id.strip())
    if user is None:
        raise UserNotFoundError(f"User '{user_id.strip()}' was not found.")
    updated_user = crud.update_user_type(db, user, user_type)
    return UserProfileResponse.model_validate(updated_user)


def update_user_schedule(db: Session, user_id: str, gym_time: str) -> UserProfileResponse:
    profile = get_user_profile(db, user_id)
    normalized_gym_time = normalize_gym_time(gym_time)
    user = crud.get_user_by_user_id(db, profile.user_id)
    if user is None:
        raise UserNotFoundError(f"User '{profile.user_id}' was not found.")
    updated_user = crud.update_user_schedule(db, user, normalized_gym_time)
    return UserProfileResponse.model_validate(updated_user)

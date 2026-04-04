from sqlalchemy.orm import Session

from app import crud
from app.schemas import FeedbackCreateRequest, FeedbackResponse


def create_feedback(db: Session, payload: FeedbackCreateRequest) -> FeedbackResponse:
    user_id = payload.user_id.strip()
    if not user_id:
        raise ValueError("user_id must not be empty.")

    user = crud.get_user_by_user_id(db, user_id)
    if user is None:
        raise ValueError(f"User '{user_id}' was not found.")

    feedback = crud.create_feedback(
        db,
        user=user,
        difficulty=payload.difficulty,
        energy_level=payload.energy_level,
        pain=payload.pain,
    )
    return FeedbackResponse.model_validate(
        {
            "user_id": user.user_id,
            "difficulty": feedback.difficulty,
            "energy_level": feedback.energy_level,
            "pain": feedback.pain,
        }
    )


def get_latest_feedback(db: Session, user_id: str) -> FeedbackResponse | None:
    normalized_user_id = user_id.strip()
    if not normalized_user_id:
        raise ValueError("user_id must not be empty.")

    user = crud.get_user_by_user_id(db, normalized_user_id)
    if user is None:
        return None

    latest_feedback = crud.get_latest_feedback(db, user)
    if latest_feedback is None:
        return None

    return FeedbackResponse.model_validate(
        {
            "user_id": user.user_id,
            "difficulty": latest_feedback.difficulty,
            "energy_level": latest_feedback.energy_level,
            "pain": latest_feedback.pain,
        }
    )

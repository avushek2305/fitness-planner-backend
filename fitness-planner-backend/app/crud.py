from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FeedbackModel, PlanLogModel, UserModel


def get_user_by_user_id(db: Session, user_id: str) -> UserModel | None:
    return db.scalar(select(UserModel).where(UserModel.user_id == user_id))


def create_user(
    db: Session,
    *,
    user_id: str,
    password_hash: str,
    gym_time: str,
    goal: str,
    workout_days_per_week: int,
    user_type: str,
) -> UserModel:
    user = UserModel(
        user_id=user_id,
        password_hash=password_hash,
        gym_time=gym_time,
        goal=goal,
        workout_days_per_week=workout_days_per_week,
        user_type=user_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_schedule(db: Session, user: UserModel, gym_time: str) -> UserModel:
    user.gym_time = gym_time
    db.commit()
    db.refresh(user)
    return user


def update_user_type(db: Session, user: UserModel, user_type: str) -> UserModel:
    user.user_type = user_type
    db.commit()
    db.refresh(user)
    return user


def create_feedback(
    db: Session,
    *,
    user: UserModel,
    difficulty: int,
    energy_level: int,
    pain: bool,
) -> FeedbackModel:
    feedback = FeedbackModel(
        user_id=user.id,
        difficulty=difficulty,
        energy_level=energy_level,
        pain=pain,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_latest_feedback(db: Session, user: UserModel) -> FeedbackModel | None:
    statement = (
        select(FeedbackModel)
        .where(FeedbackModel.user_id == user.id)
        .order_by(FeedbackModel.created_at.desc(), FeedbackModel.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def get_plan_log_for_date(db: Session, user: UserModel, log_date: date) -> PlanLogModel | None:
    statement = select(PlanLogModel).where(
        PlanLogModel.user_id == user.id,
        PlanLogModel.log_date == log_date,
    )
    return db.scalar(statement)


def upsert_plan_log(
    db: Session,
    *,
    user: UserModel,
    log_date: date,
    status: str,
    score: float,
    fallback_choice: str | None = None,
) -> PlanLogModel:
    existing_log = get_plan_log_for_date(db, user, log_date)
    if existing_log is None:
        existing_log = PlanLogModel(
            user_id=user.id,
            log_date=log_date,
            status=status,
            score=score,
            fallback_choice=fallback_choice,
        )
        db.add(existing_log)
    else:
        existing_log.status = status
        existing_log.score = score
        existing_log.fallback_choice = fallback_choice

    db.commit()
    db.refresh(existing_log)
    return existing_log


def list_recent_plan_logs(
    db: Session,
    *,
    user: UserModel,
    end_date: date,
    days: int = 7,
) -> list[PlanLogModel]:
    start_date = end_date - timedelta(days=days - 1)
    statement = (
        select(PlanLogModel)
        .where(
            PlanLogModel.user_id == user.id,
            PlanLogModel.log_date >= start_date,
            PlanLogModel.log_date <= end_date,
        )
        .order_by(PlanLogModel.log_date.desc(), PlanLogModel.id.desc())
    )
    return list(db.scalars(statement))


def get_user_by_credentials(db: Session, user_id: str) -> UserModel | None:
    return get_user_by_user_id(db, user_id)

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app import crud
from app.planner import parse_time_for_day, parse_time_for_today
from app.schemas import UserType

_STATUS_TO_SCORE = {
    "completed": 1.0,
    "partial": 0.5,
    "missed": 0.0,
}


def _get_user(db: Session, user_id: str):
    normalized_user_id = user_id.strip()
    if not normalized_user_id:
        raise ValueError("user_id must not be empty.")

    user = crud.get_user_by_user_id(db, normalized_user_id)
    if user is None:
        raise ValueError(f"User '{normalized_user_id}' was not found.")

    return user


def _calculate_completed_streak(db: Session, user, anchor_date: date) -> int:
    streak = 0
    current_date = anchor_date

    while True:
        log = crud.get_plan_log_for_date(db, user, current_date)
        if log is None or log.status != "completed":
            break
        streak += 1
        current_date -= timedelta(days=1)

    return streak


def _build_recent_activity(
    db: Session,
    *,
    user,
    gym_time: str,
    current_time: datetime,
    days: int = 7,
) -> list[str]:
    workout_time = parse_time_for_today(gym_time)
    missed_cutoff = workout_time + timedelta(hours=1)
    today_log = crud.get_plan_log_for_date(db, user, current_time.date())

    window_end = current_time.date()
    if today_log is None and current_time <= missed_cutoff:
        window_end = current_time.date() - timedelta(days=1)

    recent_logs = crud.list_recent_plan_logs(
        db,
        user=user,
        end_date=window_end,
        days=days,
    )
    if not recent_logs:
        return []

    log_map = {log.log_date: log.status for log in recent_logs}
    activity: list[str] = []
    for offset in range(days):
        target_date = window_end - timedelta(days=offset)
        activity.append(log_map.get(target_date, "missed"))

    return activity


def record_workout_completion(
    db: Session,
    user_id: str,
    completion_type: str = "full",
    completed_on: date | None = None,
    fallback_choice: str | None = None,
) -> tuple[int, float]:
    user = _get_user(db, user_id)
    completion_date = completed_on or date.today()

    if completion_type == "fallback" and not fallback_choice:
        raise ValueError("fallback_choice is required for fallback completion.")

    status_map = {
        "full": "completed",
        "fallback": "partial",
        "missed": "missed",
    }
    if completion_type not in status_map:
        raise ValueError("Unsupported completion_type.")

    status_value = status_map[completion_type]
    score = _STATUS_TO_SCORE[status_value]
    crud.upsert_plan_log(
        db,
        user=user,
        log_date=completion_date,
        status=status_value,
        score=score,
        fallback_choice=fallback_choice if completion_type == "fallback" else None,
    )

    if status_value != "completed":
        return 0, score

    return _calculate_completed_streak(db, user, completion_date), score


def get_today_score(db: Session, user_id: str, gym_time: str, now: datetime | None = None) -> float:
    user = _get_user(db, user_id)
    current_time = now or datetime.now()
    today = current_time.date()

    today_log = crud.get_plan_log_for_date(db, user, today)
    if today_log is not None:
        return today_log.score

    workout_time = parse_time_for_today(gym_time)
    missed_cutoff = workout_time + timedelta(hours=1)

    if current_time > missed_cutoff:
        crud.upsert_plan_log(
            db,
            user=user,
            log_date=today,
            status="missed",
            score=0.0,
        )
        return 0.0

    return 0.0


def get_recent_activity(db: Session, user_id: str, gym_time: str, now: datetime | None = None) -> list[str]:
    user = _get_user(db, user_id)
    current_time = now or datetime.now()
    return _build_recent_activity(db, user=user, gym_time=gym_time, current_time=current_time)


def get_user_type(db: Session, user_id: str, gym_time: str, now: datetime | None = None) -> UserType:
    user = _get_user(db, user_id)
    current_time = now or datetime.now()
    recent_activity = _build_recent_activity(db, user=user, gym_time=gym_time, current_time=current_time)

    if not recent_activity:
        return "beginner"

    completed_days = sum(1 for status in recent_activity if status == "completed")
    missed_days = sum(1 for status in recent_activity if status == "missed")

    if missed_days >= 2:
        return "irregular"

    if completed_days >= 5:
        return "intermediate"

    return "beginner"


def sync_streak_for_today(db: Session, user_id: str, gym_time: str, now: datetime | None = None) -> int:
    user = _get_user(db, user_id)
    current_time = now or datetime.now()
    today = current_time.date()
    today_log = crud.get_plan_log_for_date(db, user, today)

    if today_log is not None:
        if today_log.status == "completed":
            return _calculate_completed_streak(db, user, today)
        return 0

    workout_time = parse_time_for_day(gym_time, datetime.combine(today, datetime.min.time()))
    missed_cutoff = workout_time + timedelta(hours=1)
    if current_time > missed_cutoff:
        crud.upsert_plan_log(
            db,
            user=user,
            log_date=today,
            status="missed",
            score=0.0,
        )
        return 0

    return _calculate_completed_streak(db, user, today - timedelta(days=1))

from datetime import datetime, timedelta

from app.messaging import get_coaching_message
from app.schemas import DayPlanResponse, FeedbackResponse, MealItem, TimeBlocks, WorkoutItem


TIME_INPUT_FORMATS = ("%H:%M", "%I:%M %p")
TIME_OUTPUT_FORMAT = "%H:%M"


def parse_time_for_today(gym_time: str) -> datetime:
    return parse_time_for_day(gym_time)


def parse_time_for_day(gym_time: str, reference_date: datetime | None = None) -> datetime:
    normalized_value = gym_time.strip()
    base_date = reference_date or datetime.now()
    for time_format in TIME_INPUT_FORMATS:
        try:
            candidate = normalized_value.upper() if "%p" in time_format else normalized_value
            parsed_time = datetime.strptime(candidate, time_format)
            return parsed_time.replace(
                year=base_date.year,
                month=base_date.month,
                day=base_date.day,
            )
        except ValueError:
            continue

    raise ValueError("gym_time must be in the format '19:00'.")


def _parse_gym_time(gym_time: str) -> datetime:
    return parse_time_for_today(gym_time)


def _format_time(value: datetime) -> str:
    return value.strftime(TIME_OUTPUT_FORMAT)


def normalize_gym_time(gym_time: str) -> str:
    if not gym_time.strip():
        raise ValueError("gym_time must not be empty.")
    return _format_time(_parse_gym_time(gym_time))


def _build_time_blocks(gym_time: str) -> TimeBlocks:
    workout_time = _parse_gym_time(gym_time)
    pre_workout_time = workout_time - timedelta(minutes=45)
    post_workout_time = workout_time + timedelta(minutes=75)

    return TimeBlocks(
        pre_workout_time=_format_time(pre_workout_time),
        workout_time=_format_time(workout_time),
        post_workout_time=_format_time(post_workout_time),
    )


def _append_note(existing_note: str | None, new_note: str) -> str:
    if not existing_note:
        return new_note
    return f"{existing_note} {new_note}"


def _build_workout_by_user_type(user_type: str) -> list[WorkoutItem]:
    if user_type == "beginner":
        return [
            WorkoutItem(name="Warmup walk", duration_minutes=5, notes="Easy pace."),
            WorkoutItem(name="Bodyweight squats", sets=2, reps=10),
            WorkoutItem(name="Wall push-ups", sets=2, reps=8),
            WorkoutItem(name="Standing stretch", duration_minutes=4),
        ]

    if user_type == "irregular":
        return [
            WorkoutItem(name="Brisk walk", duration_minutes=10, notes="Keep it light and finish the session."),
            WorkoutItem(name="Bodyweight squats", sets=2, reps=10),
            WorkoutItem(name="Push-ups", sets=1, reps=8, notes="Focus on consistency, not intensity."),
        ]

    return [
        WorkoutItem(name="Brisk walk", duration_minutes=10, notes="Easy pace to warm up."),
        WorkoutItem(name="Bodyweight squats", sets=3, reps=15),
        WorkoutItem(name="Push-ups", sets=3, reps=12),
        WorkoutItem(name="Plank", duration_minutes=3, notes="Break into 60-second rounds if needed."),
    ]


def _increase_intensity(workout: list[WorkoutItem]) -> list[WorkoutItem]:
    adjusted_workout: list[WorkoutItem] = []
    for item in workout:
        adjusted_workout.append(
            item.model_copy(
                update={
                    "sets": item.sets if item.sets is not None else None,
                    "reps": item.reps + 2 if item.reps is not None else None,
                    "duration_minutes": item.duration_minutes if item.duration_minutes is not None else None,
                    "notes": _append_note(item.notes, "Reps increased slightly because the previous session felt manageable."),
                }
            )
        )
    return adjusted_workout


def _reduce_intensity(workout: list[WorkoutItem]) -> list[WorkoutItem]:
    adjusted_workout: list[WorkoutItem] = []
    for item in workout:
        adjusted_workout.append(
            item.model_copy(
                update={
                    "sets": max(1, item.sets - 1) if item.sets is not None else None,
                    "reps": max(1, item.reps - 2) if item.reps is not None else None,
                    "duration_minutes": max(1, item.duration_minutes - 2) if item.duration_minutes is not None else None,
                    "notes": _append_note(item.notes, "Intensity reduced slightly to support better recovery."),
                }
            )
        )
    return adjusted_workout


def _reduce_workout_volume(workout: list[WorkoutItem]) -> list[WorkoutItem]:
    adjusted_workout: list[WorkoutItem] = []
    for item in workout:
        adjusted_workout.append(
            item.model_copy(
                update={
                    "sets": max(1, item.sets - 1) if item.sets is not None else None,
                    "duration_minutes": max(1, item.duration_minutes - 3) if item.duration_minutes is not None else None,
                    "notes": _append_note(item.notes, "Workout volume reduced because reported energy was low."),
                }
            )
        )
    return adjusted_workout


def _increase_workout_volume(workout: list[WorkoutItem]) -> list[WorkoutItem]:
    adjusted_workout: list[WorkoutItem] = []
    for item in workout:
        adjusted_workout.append(
            item.model_copy(
                update={
                    "sets": item.sets + 1 if item.sets is not None else None,
                    "reps": item.reps + 1 if item.reps is not None else None,
                    "duration_minutes": item.duration_minutes + 2 if item.duration_minutes is not None else None,
                    "notes": _append_note(item.notes, "Session volume increased slightly for a lower weekly frequency."),
                }
            )
        )
    return adjusted_workout


def _apply_preference_adjustments(
    workout: list[WorkoutItem],
    goal: str,
    workout_days_per_week: int,
) -> list[WorkoutItem]:
    adjusted_workout = workout

    if workout_days_per_week <= 3:
        adjusted_workout = _increase_workout_volume(adjusted_workout)
    elif workout_days_per_week >= 5:
        adjusted_workout = _reduce_workout_volume(adjusted_workout)
        adjusted_workout = [
            item.model_copy(
                update={
                    "notes": _append_note(
                        item.notes,
                        "Per-session volume trimmed because you train more often each week.",
                    )
                }
            )
            for item in adjusted_workout
        ]

    if goal == "muscle_gain":
        adjusted_workout = [
            item.model_copy(
                update={
                    "notes": _append_note(
                        item.notes,
                        f"Built for {workout_days_per_week} training days per week with a muscle gain focus.",
                    )
                }
            )
            for item in adjusted_workout
        ]
    else:
        adjusted_workout = [
            item.model_copy(
                update={
                    "notes": _append_note(
                        item.notes,
                        f"Built for {workout_days_per_week} training days per week with a fat loss focus.",
                    )
                }
            )
            for item in adjusted_workout
        ]

    return adjusted_workout


def _apply_feedback_adjustments(
    workout: list[WorkoutItem],
    feedback: FeedbackResponse | None,
) -> list[WorkoutItem]:
    if feedback is None:
        return workout

    if feedback.pain:
        return _reduce_intensity(workout)

    adjusted_workout = workout

    if feedback.difficulty <= 2:
        adjusted_workout = _increase_intensity(adjusted_workout)
    elif feedback.difficulty >= 4:
        adjusted_workout = _reduce_intensity(adjusted_workout)

    if feedback.energy_level <= 2:
        adjusted_workout = _reduce_workout_volume(adjusted_workout)

    return adjusted_workout


def _apply_recent_activity_adjustments(
    workout: list[WorkoutItem],
    recent_activity: list[str] | None,
) -> list[WorkoutItem]:
    if not recent_activity:
        return workout

    completed_days = sum(1 for status in recent_activity if status == "completed")
    partial_days = sum(1 for status in recent_activity if status == "partial")
    missed_days = sum(1 for status in recent_activity if status == "missed")

    adjusted_workout = workout

    if completed_days >= 5 and missed_days == 0:
        adjusted_workout = _increase_intensity(adjusted_workout)
        adjusted_workout = [
            item.model_copy(
                update={
                    "notes": _append_note(
                        item.notes,
                        "Intensity nudged up because the last 7 days were consistent.",
                    )
                }
            )
            for item in adjusted_workout
        ]
        return adjusted_workout

    if missed_days >= 2:
        adjusted_workout = _reduce_intensity(adjusted_workout)
        adjusted_workout = [
            item.model_copy(
                update={
                    "notes": _append_note(
                        item.notes,
                        "Intensity lowered to rebuild consistency over the last 7 days.",
                    )
                }
            )
            for item in adjusted_workout
        ]
        return adjusted_workout

    if partial_days >= 2:
        adjusted_workout = _reduce_workout_volume(adjusted_workout)
        adjusted_workout = [
            item.model_copy(
                update={
                    "notes": _append_note(
                        item.notes,
                        "Volume trimmed because recent sessions were only partially completed.",
                    )
                }
            )
            for item in adjusted_workout
        ]
        return adjusted_workout

    return adjusted_workout


def _build_next_action(
    time_blocks: TimeBlocks,
    current_time: datetime,
    user_id: str,
    goal: str,
    user_type: str,
    streak: int,
) -> str:
    pre_workout_time = _parse_gym_time(time_blocks.pre_workout_time)
    workout_time = _parse_gym_time(time_blocks.workout_time)
    post_workout_time = _parse_gym_time(time_blocks.post_workout_time)
    workout_end_time = workout_time + timedelta(hours=1)

    if current_time < pre_workout_time:
        return get_coaching_message(
            "pre_workout_meal",
            user_id=user_id,
            goal=goal,
            user_type=user_type,
            streak=streak,
        )
    if current_time < workout_time:
        return get_coaching_message(
            "get_ready",
            user_id=user_id,
            goal=goal,
            user_type=user_type,
            streak=streak,
        )
    if current_time < workout_end_time:
        return get_coaching_message(
            "workout_now",
            user_id=user_id,
            goal=goal,
            user_type=user_type,
            streak=streak,
        )
    if current_time < post_workout_time:
        return get_coaching_message(
            "post_workout_meal",
            user_id=user_id,
            goal=goal,
            user_type=user_type,
            streak=streak,
        )
    return get_coaching_message(
        "done",
        user_id=user_id,
        goal=goal,
        user_type=user_type,
        streak=streak,
    )


def _build_status(time_blocks: TimeBlocks, current_time: datetime) -> str:
    workout_time = _parse_gym_time(time_blocks.workout_time)
    post_workout_time = _parse_gym_time(time_blocks.post_workout_time)
    workout_end_time = workout_time + timedelta(hours=1)

    if current_time < workout_time:
        return "pre_workout"
    if current_time < workout_end_time:
        return "workout"
    if current_time < post_workout_time:
        return "post_workout"
    return "done"


def _build_base_plan(
    user_id: str,
    gym_time: str,
    goal: str,
    feedback: FeedbackResponse | None,
    streak: int,
    today_score: float,
    user_type: str,
    recent_activity: list[str] | None,
    workout_days_per_week: int,
) -> DayPlanResponse:
    """Return a baseline day plan that can later be personalized per user."""
    now = datetime.now()
    time_blocks = _build_time_blocks(gym_time)
    current_time = _format_time(now)
    meal_note = (
        "Slight calorie surplus with extra protein for recovery."
        if goal == "muscle_gain"
        else "Keep portions controlled and prioritize lean protein."
    )
    base_workout = _build_workout_by_user_type(user_type)
    preference_adjusted_workout = _apply_preference_adjustments(
        base_workout,
        goal=goal,
        workout_days_per_week=workout_days_per_week,
    )
    activity_adjusted_workout = _apply_recent_activity_adjustments(
        preference_adjusted_workout,
        recent_activity,
    )

    return DayPlanResponse(
        day=1,
        workout=_apply_feedback_adjustments(activity_adjusted_workout, feedback),
        meals=[
            MealItem(
                name="Breakfast oats bowl",
                calories=420,
                protein_grams=22,
                notes="Oats, Greek yogurt, berries, and chia seeds.",
            ),
            MealItem(
                name="Grilled chicken rice bowl",
                calories=610,
                protein_grams=42,
                notes=meal_note,
            ),
            MealItem(
                name="Salmon with sweet potato",
                calories=560,
                protein_grams=38,
                notes="Add greens on the side for fiber.",
            ),
        ],
        time_blocks=time_blocks,
        next_action=_build_next_action(time_blocks, now, user_id, goal, user_type, streak),
        current_time=current_time,
        status=_build_status(time_blocks, now),
        streak=streak,
        today_score=today_score,
        user_type=user_type,
        workout_days_per_week=workout_days_per_week,
    )


def get_today_plan(
    user_id: str,
    gym_time: str,
    goal: str,
    feedback: FeedbackResponse | None = None,
    streak: int = 0,
    today_score: float = 0.0,
    user_type: str = "beginner",
    recent_activity: list[str] | None = None,
    workout_days_per_week: int = 4,
) -> DayPlanResponse:
    """Return today's hardcoded plan.

    The user_id is accepted now so the planner can later branch into
    user-specific templates, preferences, and progression logic.
    """
    if not user_id.strip():
        raise ValueError("user_id must not be empty.")
    normalized_gym_time = normalize_gym_time(gym_time)

    return _build_base_plan(
        user_id=user_id,
        gym_time=normalized_gym_time,
        goal=goal,
        feedback=feedback,
        streak=streak,
        today_score=today_score,
        user_type=user_type,
        recent_activity=recent_activity,
        workout_days_per_week=workout_days_per_week,
    )

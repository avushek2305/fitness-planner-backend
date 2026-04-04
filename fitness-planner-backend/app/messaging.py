import random
from datetime import date

_STREAK_ACTIONS = {"pre_workout_meal", "get_ready", "workout_now"}
_IDENTITY_ACTIONS = {"pre_workout_meal", "get_ready", "workout_now"}

_IDENTITY_MESSAGE_DATES: dict[str, date] = {}

_MESSAGES = {
    "beginner": {
        "pre_workout_meal": [
            "Start small. Just show up.",
            "Keep it easy. Have a light bite and get ready.",
            "One step at a time. Fuel up and head in.",
        ],
        "get_ready": [
            "Start small. Just show up.",
            "You only need to begin. Get ready now.",
            "Easy win today. Get dressed and go.",
        ],
        "workout_now": [
            "Nice and steady. Start your workout.",
            "You are doing well. Begin the session.",
            "Keep it simple. Start moving now.",
        ],
        "post_workout_meal": [
            "Nice work. Time for protein.",
            "Good start today. Refuel now.",
            "You showed up. Now recover well.",
        ],
        "done": [
            "Good work today. Keep building.",
            "Nice job. That is how progress starts.",
            "You got it done today. Be proud of that.",
        ],
    },
    "intermediate": {
        "pre_workout_meal": [
            "Fuel up. Gym in 45 min.",
            "Get your meal in. It is almost go time.",
            "Eat light and get focused.",
        ],
        "get_ready": [
            "Let's go. Time to train.",
            "Get ready. It is almost workout time.",
            "Lock in. Gym is next.",
        ],
        "workout_now": [
            "Let's go. Time to train.",
            "Start the workout. No delay.",
            "You know the drill. Get after it.",
        ],
        "post_workout_meal": [
            "Time for protein.",
            "Recover well. Get your meal in.",
            "Session done. Refuel properly.",
        ],
        "done": [
            "Good work. Recover and come back stronger.",
            "Solid session. Stay consistent.",
            "Done. That is how you keep momentum.",
        ],
    },
    "irregular": {
        "pre_workout_meal": [
            "You've missed before. Don't skip today.",
            "No drifting today. Eat light and get ready.",
            "Show up this time. Gym is coming.",
        ],
        "get_ready": [
            "You've missed before. Don't skip today.",
            "Get ready now. No excuses today.",
            "Break the pattern. Head to the gym.",
        ],
        "workout_now": [
            "Time to train. No excuses.",
            "Do not overthink it. Start now.",
            "Just get through this session today.",
        ],
        "post_workout_meal": [
            "Good. Now recover and keep the streak alive.",
            "Nice. Get your protein in and reset.",
            "You showed up. Finish recovery properly.",
        ],
        "done": [
            "You got through it. Come back tomorrow.",
            "Done. Build consistency from here.",
            "Good. One session at a time now.",
        ],
    },
}

_GOAL_IDENTITY_MESSAGES = {
    "muscle_gain": [
        "You said you want broader shoulders.",
        "You are building size one session at a time.",
    ],
    "fat_loss": [
        "You said you want a leaner body.",
        "Consistency is how you lean out.",
    ],
}

_GENERIC_IDENTITY_MESSAGES = [
    "Consistency builds your physique, not motivation.",
    "One missed day becomes a habit.",
]


def _should_use_identity_message(user_id: str, action_key: str) -> bool:
    if action_key not in _IDENTITY_ACTIONS:
        return False

    today = date.today()
    return _IDENTITY_MESSAGE_DATES.get(user_id) != today


def _get_identity_message(user_id: str, goal: str) -> str:
    today = date.today()
    _IDENTITY_MESSAGE_DATES[user_id] = today

    goal_messages = _GOAL_IDENTITY_MESSAGES.get(goal, [])
    all_messages = [*goal_messages, *_GENERIC_IDENTITY_MESSAGES]
    return random.choice(all_messages)


def get_coaching_message(
    action_key: str,
    user_id: str,
    goal: str,
    user_type: str,
    streak: int = 0,
) -> str:
    if _should_use_identity_message(user_id, action_key):
        return _get_identity_message(user_id, goal)

    if streak >= 3 and action_key in _STREAK_ACTIONS:
        return f"You're on a {streak} day streak. Don't break it."

    if streak == 0 and action_key in _STREAK_ACTIONS:
        return "Let's restart. Day 1 today."

    messages = _MESSAGES.get(user_type, _MESSAGES["beginner"]).get(action_key)
    if not messages:
        raise ValueError(f"Unknown action key: {action_key}")
    return random.choice(messages)

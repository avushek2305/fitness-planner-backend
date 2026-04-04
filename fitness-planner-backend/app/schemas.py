from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

UserType = Literal["beginner", "intermediate", "irregular"]
GoalType = Literal["muscle_gain", "fat_loss"]
PlanStatus = Literal["pre_workout", "workout", "post_workout", "done"]
CompletionType = Literal["full", "fallback", "missed"]

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: T


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
    code: int


class WorkoutItem(BaseModel):
    name: str
    sets: int | None = Field(default=None, ge=1)
    reps: int | None = Field(default=None, ge=1)
    duration_minutes: int | None = Field(default=None, ge=1)
    notes: str | None = None


class MealItem(BaseModel):
    name: str
    calories: int | None = Field(default=None, ge=0)
    protein_grams: int | None = Field(default=None, ge=0)
    notes: str | None = None


class TimeBlocks(BaseModel):
    pre_workout_time: str
    workout_time: str
    post_workout_time: str


class PlanResponse(BaseModel):
    day: int = Field(..., ge=1)
    workout: list[WorkoutItem]
    meals: list[MealItem]
    time_blocks: TimeBlocks
    next_action: str
    current_time: str
    status: PlanStatus
    streak: int = Field(..., ge=0)
    today_score: float = Field(..., ge=0, le=1)
    user_type: UserType
    workout_days_per_week: int = Field(..., ge=3, le=6)


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., min_length=1)
    gym_time: str = Field(..., min_length=1, description="Gym time in the format '19:00'.")
    goal: GoalType
    workout_days_per_week: int = Field(..., ge=3, le=6)
    user_type: UserType


class Feedback(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., min_length=1)
    difficulty: int = Field(..., ge=1, le=5)
    energy_level: int = Field(..., ge=1, le=5)
    pain: bool


class UserCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    gym_time: str = Field(..., min_length=1, description="Gym time in the format '19:00'.")
    goal: GoalType
    workout_days_per_week: int = Field(..., ge=3, le=6)
    password: str = Field(..., min_length=8)


class UserScheduleUpdateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    gym_time: str = Field(..., min_length=1, description="Gym time in the format '19:00'.")


class ScheduleUpdateResponse(BaseModel):
    user_id: str
    gym_time: str
    plan: PlanResponse


class FeedbackCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    difficulty: int = Field(..., ge=1, le=5)
    energy_level: int = Field(..., ge=1, le=5)
    pain: bool


class WorkoutCompletionRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    completion_type: CompletionType = "full"
    fallback_choice: str | None = None


class WorkoutCompletionResponse(BaseModel):
    user_id: str
    streak: int = Field(..., ge=0)
    today_score: float = Field(..., ge=0, le=1)
    user_type: UserType


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User


# Backward-compatible aliases for the rest of the codebase.
DayPlanResponse = PlanResponse
UserProfileCreateRequest = UserCreateRequest
UserProfileResponse = User
UserScheduleUpdateResponse = ScheduleUpdateResponse
FeedbackResponse = Feedback

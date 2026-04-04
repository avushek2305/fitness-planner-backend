import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import crud
from app.auth import create_access_token, get_current_user_id, verify_password
from app.database import get_db, init_db
from app.feedback_store import create_feedback, get_latest_feedback
from app.planner import get_today_plan
from app.schemas import (
    ApiResponse,
    AuthTokenResponse,
    ErrorResponse,
    Feedback,
    FeedbackCreateRequest,
    LoginRequest,
    PlanResponse,
    ScheduleUpdateResponse,
    User,
    UserCreateRequest,
    UserScheduleUpdateRequest,
    WorkoutCompletionRequest,
    WorkoutCompletionResponse,
)
from app.streak_store import (
    get_recent_activity,
    get_today_score,
    get_user_type,
    record_workout_completion,
    sync_streak_for_today,
)
from app.user_store import (
    UserAlreadyExistsError,
    UserNotFoundError,
    create_user_profile,
    get_user_profile,
    set_user_type,
    update_user_schedule,
)

logger = logging.getLogger(__name__)


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(message=message, code=status_code).model_dump(),
    )


def _build_plan_response(db: Session, user_id: str) -> PlanResponse:
    profile = get_user_profile(db, user_id)
    latest_feedback = get_latest_feedback(db, profile.user_id)
    streak = sync_streak_for_today(db, profile.user_id, profile.gym_time)
    today_score = get_today_score(db, profile.user_id, profile.gym_time)
    recent_activity = get_recent_activity(db, profile.user_id, profile.gym_time)
    user_type = get_user_type(db, profile.user_id, profile.gym_time)
    updated_profile = set_user_type(db, profile.user_id, user_type)

    return get_today_plan(
        user_id=updated_profile.user_id,
        gym_time=updated_profile.gym_time,
        goal=updated_profile.goal,
        feedback=latest_feedback,
        streak=streak,
        today_score=today_score,
        user_type=user_type,
        recent_activity=recent_activity,
        workout_days_per_week=updated_profile.workout_days_per_week,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fitness Planner API",
        version="0.1.0",
        description="Minimal FastAPI backend that returns a structured daily fitness plan.",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else None
        message = "Validation error."
        if first_error and first_error.get("msg"):
            message = str(first_error["msg"])
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, message)

    @app.exception_handler(Exception)
    async def handle_internal_server_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error.",
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        return _error_response(exc.status_code, str(exc.detail))

    @app.post(
        "/signup",
        response_model=ApiResponse[User],
        status_code=status.HTTP_201_CREATED,
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request."},
            409: {"model": ErrorResponse, "description": "User already exists."},
            500: {"model": ErrorResponse, "description": "Internal server error."},
        },
        tags=["auth"],
    )
    async def signup(
        payload: UserCreateRequest,
        db: Session = Depends(get_db),
    ) -> ApiResponse[User] | JSONResponse:
        try:
            created_user = create_user_profile(db, payload)
            return ApiResponse[User](data=created_user)
        except UserAlreadyExistsError as exc:
            return _error_response(status.HTTP_409_CONFLICT, str(exc))
        except ValueError as exc:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.post(
        "/login",
        response_model=ApiResponse[AuthTokenResponse],
        status_code=status.HTTP_200_OK,
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request."},
            401: {"model": ErrorResponse, "description": "Invalid credentials."},
            500: {"model": ErrorResponse, "description": "Internal server error."},
        },
        tags=["auth"],
    )
    async def login(
        payload: LoginRequest,
        db: Session = Depends(get_db),
    ) -> ApiResponse[AuthTokenResponse] | JSONResponse:
        user = crud.get_user_by_credentials(db, payload.user_id.strip())
        if user is None or not verify_password(payload.password, user.password_hash):
            return _error_response(status.HTTP_401_UNAUTHORIZED, "Invalid user_id or password.")

        return ApiResponse[AuthTokenResponse](
            data=AuthTokenResponse(
                access_token=create_access_token(user.user_id),
                user=User.model_validate(user),
            )
        )

    @app.put(
        "/user/schedule",
        response_model=ApiResponse[ScheduleUpdateResponse],
        status_code=status.HTTP_200_OK,
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request."},
            404: {"model": ErrorResponse, "description": "User not found."},
            500: {"model": ErrorResponse, "description": "Internal server error."},
        },
        tags=["users"],
    )
    async def update_schedule(
        payload: UserScheduleUpdateRequest,
        db: Session = Depends(get_db),
    ) -> ApiResponse[ScheduleUpdateResponse] | JSONResponse:
        try:
            profile = update_user_schedule(db, payload.user_id, payload.gym_time)
            recalculated_plan = _build_plan_response(db, profile.user_id)
            response_payload = ScheduleUpdateResponse(
                user_id=profile.user_id,
                gym_time=profile.gym_time,
                plan=recalculated_plan,
            )
            return ApiResponse[ScheduleUpdateResponse](data=response_payload)
        except UserNotFoundError as exc:
            return _error_response(status.HTTP_404_NOT_FOUND, str(exc))
        except ValueError as exc:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.post(
        "/complete",
        response_model=ApiResponse[WorkoutCompletionResponse],
        status_code=status.HTTP_200_OK,
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request."},
            404: {"model": ErrorResponse, "description": "User not found."},
            500: {"model": ErrorResponse, "description": "Internal server error."},
        },
        tags=["workouts"],
    )
    async def complete_workout(
        payload: WorkoutCompletionRequest,
        db: Session = Depends(get_db),
    ) -> ApiResponse[WorkoutCompletionResponse] | JSONResponse:
        try:
            profile = get_user_profile(db, payload.user_id)
            streak, today_score = record_workout_completion(
                db,
                profile.user_id,
                completion_type=payload.completion_type,
                fallback_choice=payload.fallback_choice,
            )
            user_type = get_user_type(db, profile.user_id, profile.gym_time)
            set_user_type(db, profile.user_id, user_type)
            return ApiResponse[WorkoutCompletionResponse](
                data=WorkoutCompletionResponse(
                    user_id=profile.user_id,
                    streak=streak,
                    today_score=today_score,
                    user_type=user_type,
                )
            )
        except UserNotFoundError as exc:
            return _error_response(status.HTTP_404_NOT_FOUND, str(exc))
        except ValueError as exc:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.post(
        "/feedback",
        response_model=ApiResponse[Feedback],
        status_code=status.HTTP_201_CREATED,
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request."},
            404: {"model": ErrorResponse, "description": "User not found."},
            500: {"model": ErrorResponse, "description": "Internal server error."},
        },
        tags=["feedback"],
    )
    async def create_user_feedback(
        payload: FeedbackCreateRequest,
        current_user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db),
    ) -> ApiResponse[Feedback] | JSONResponse:
        try:
            if payload.user_id != current_user_id:
                return _error_response(status.HTTP_403_FORBIDDEN, "You can only submit feedback for your own account.")
            get_user_profile(db, payload.user_id)
            saved_feedback = create_feedback(db, payload)
            return ApiResponse[Feedback](data=saved_feedback)
        except UserNotFoundError as exc:
            return _error_response(status.HTTP_404_NOT_FOUND, str(exc))
        except ValueError as exc:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.get(
        "/plan/{user_id}",
        response_model=ApiResponse[PlanResponse],
        response_model_exclude_none=True,
        responses={
            400: {"model": ErrorResponse, "description": "Invalid request."},
            404: {"model": ErrorResponse, "description": "User not found."},
            500: {"model": ErrorResponse, "description": "Internal server error."},
        },
        tags=["plans"],
    )
    async def read_plan(
        user_id: str = Path(..., min_length=1),
        current_user_id: str = Depends(get_current_user_id),
        db: Session = Depends(get_db),
    ) -> ApiResponse[PlanResponse] | JSONResponse:
        try:
            if user_id != current_user_id:
                return _error_response(status.HTTP_403_FORBIDDEN, "You can only access your own plan.")
            return ApiResponse[PlanResponse](data=_build_plan_response(db, user_id))
        except UserNotFoundError as exc:
            return _error_response(status.HTTP_404_NOT_FOUND, str(exc))
        except ValueError as exc:
            return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    return app


app = create_app()

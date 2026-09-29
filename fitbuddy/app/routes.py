import json
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gemini_flash_generator import (
    generate_nutrition_tip_with_flash,
)
from app.ai.gemini_generator import generate_workout_gemini
from app.ai.updated_plan import update_workout_plan
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import FeedbackRequest, UserInput


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


def _check_admin_token(token: str | None) -> None:
    """
    If ADMIN_TOKEN is configured, require it.
    For local development an empty token allows access.
    """

    if settings.admin_token and token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
        )


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "user_id": user.user_id,
        "name": user.name,
        "age": user.age,
        "weight": user.weight,
        "goal": user.goal,
        "intensity": user.intensity,
        "experience_level": user.experience_level,
        "workout_plan": user.workout_plan,
        "updated_plan": user.updated_plan,
        "nutrition_tip": user.nutrition_tip,
        "feedback": user.feedback,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _parse_plan(plan_text: str) -> dict:
    try:
        return json.loads(plan_text)
    except (json.JSONDecodeError, TypeError):
        return {
            "title": "Workout Plan",
            "goal": "",
            "intensity": "",
            "safety_note": "",
            "days": [],
            "raw": plan_text,
        }


def _render_result(
    request: Request,
    user: User,
    message: str | None = None,
) -> HTMLResponse:
    active_plan = user.updated_plan or user.workout_plan

    context = {
        "request": request,
        "user": user,
        "workout_plan": _parse_plan(active_plan),
        "original_plan": _parse_plan(user.workout_plan),
        "nutrition_tip": _parse_plan(user.nutrition_tip),
        "message": message,
        "demo_mode": settings.demo_mode or not settings.gemini_api_key,
    }

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context=context,
    )


@router.get(
    "/",
    response_class=HTMLResponse,
)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "demo_mode": settings.demo_mode or not settings.gemini_api_key,
        },
    )


@router.post(
    "/generate-workout",
    response_class=HTMLResponse,
)
def generate_workout_form(
    request: Request,
    user_id: str = Form(...),
    name: str = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    experience_level: str = Form("beginner"),
    db: Session = Depends(get_db),
):
    try:
        payload = UserInput(
            user_id=user_id,
            name=name,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
            experience_level=experience_level,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "error": str(exc),
                "demo_mode": settings.demo_mode or not settings.gemini_api_key,
            },
            status_code=422,
        )

    try:
        workout_plan = generate_workout_gemini(
            name=payload.name,
            age=payload.age,
            weight=payload.weight,
            goal=payload.goal,
            intensity=payload.intensity,
            experience_level=payload.experience_level,
        )

        nutrition_tip = generate_nutrition_tip_with_flash(
            goal=payload.goal,
            intensity=payload.intensity,
        )

        existing_user = db.scalar(
            select(User).where(
                User.user_id == payload.user_id
            )
        )

        if existing_user:
            existing_user.name = payload.name
            existing_user.age = payload.age
            existing_user.weight = payload.weight
            existing_user.goal = payload.goal
            existing_user.intensity = payload.intensity
            existing_user.experience_level = payload.experience_level
            existing_user.workout_plan = workout_plan
            existing_user.updated_plan = None
            existing_user.nutrition_tip = nutrition_tip
            existing_user.feedback = None

            user = existing_user

        else:
            user = User(
                user_id=payload.user_id,
                name=payload.name,
                age=payload.age,
                weight=payload.weight,
                goal=payload.goal,
                intensity=payload.intensity,
                experience_level=payload.experience_level,
                workout_plan=workout_plan,
                nutrition_tip=nutrition_tip,
            )

            db.add(user)

        db.commit()
        db.refresh(user)

        return _render_result(
            request=request,
            user=user,
            message="Your personalized plan has been generated.",
        )

    except Exception as exc:
        db.rollback()

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "error": f"Unable to generate plan: {exc}",
                "demo_mode": settings.demo_mode or not settings.gemini_api_key,
            },
            status_code=500,
        )


@router.post(
    "/submit-feedback",
    response_class=HTMLResponse,
)
def submit_feedback_form(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    payload = FeedbackRequest(
        user_id=user_id,
        feedback=feedback,
    )

    user = db.scalar(
        select(User).where(
            User.user_id == payload.user_id
        )
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    try:
        original_plan = user.updated_plan or user.workout_plan

        revised_plan = update_workout_plan(
            original_plan=original_plan,
            feedback=payload.feedback,
        )

        user.updated_plan = revised_plan
        user.feedback = payload.feedback

        db.commit()
        db.refresh(user)

        return _render_result(
            request=request,
            user=user,
            message="Your feedback has been applied and the plan was updated.",
        )

    except Exception as exc:
        db.rollback()

        return _render_result(
            request=request,
            user=user,
            message=f"Unable to update the plan: {exc}",
        )


@router.get(
    "/view-all-users",
    response_class=HTMLResponse,
)
def view_all_users(
    request: Request,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    _check_admin_token(token)

    users = db.scalars(
        select(User).order_by(User.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={
            "request": request,
            "users": users,
            "admin_token": token or "",
        },
    )


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": settings.app_version,
    }


@router.post("/api/generate-workout")
def generate_workout_api(
    payload: UserInput,
    db: Session = Depends(get_db),
):
    try:
        workout_plan = generate_workout_gemini(
            name=payload.name,
            age=payload.age,
            weight=payload.weight,
            goal=payload.goal,
            intensity=payload.intensity,
            experience_level=payload.experience_level,
        )

        nutrition_tip = generate_nutrition_tip_with_flash(
            goal=payload.goal,
            intensity=payload.intensity,
        )

        user = db.scalar(
            select(User).where(
                User.user_id == payload.user_id
            )
        )

        if user:
            user.name = payload.name
            user.age = payload.age
            user.weight = payload.weight
            user.goal = payload.goal
            user.intensity = payload.intensity
            user.experience_level = payload.experience_level
            user.workout_plan = workout_plan
            user.updated_plan = None
            user.nutrition_tip = nutrition_tip
            user.feedback = None
        else:
            user = User(
                user_id=payload.user_id,
                name=payload.name,
                age=payload.age,
                weight=payload.weight,
                goal=payload.goal,
                intensity=payload.intensity,
                experience_level=payload.experience_level,
                workout_plan=workout_plan,
                nutrition_tip=nutrition_tip,
            )

            db.add(user)

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "user": _serialize_user(user),
            "workout_plan": _parse_plan(workout_plan),
            "nutrition_tip": _parse_plan(nutrition_tip),
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post("/api/submit-feedback")
def submit_feedback_api(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.user_id == payload.user_id
        )
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    try:
        original_plan = user.updated_plan or user.workout_plan

        revised_plan = update_workout_plan(
            original_plan=original_plan,
            feedback=payload.feedback,
        )

        user.updated_plan = revised_plan
        user.feedback = payload.feedback

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": "Workout plan updated.",
            "user": _serialize_user(user),
            "updated_plan": _parse_plan(revised_plan),
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get("/api/users")
def get_users(
    token: str | None = None,
    db: Session = Depends(get_db),
):
    _check_admin_token(token)

    users = db.scalars(
        select(User).order_by(User.created_at.desc())
    ).all()

    return {
        "count": len(users),
        "users": [_serialize_user(user) for user in users],
    }


@router.get("/api/users/{user_id}")
def get_user(
    user_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    _check_admin_token(token)

    user = db.scalar(
        select(User).where(
            User.user_id == user_id
        )
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    return _serialize_user(user)


@router.delete("/api/users/{user_id}")
def delete_user(
    user_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    _check_admin_token(token)

    user = db.scalar(
        select(User).where(
            User.user_id == user_id
        )
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": f"User {user_id} deleted.",
    }
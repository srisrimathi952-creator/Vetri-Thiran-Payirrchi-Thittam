from typing import Literal

from pydantic import BaseModel, Field, field_validator


Goal = Literal[
    "weight loss",
    "muscle gain",
    "general wellness",
    "flexibility",
    "endurance",
]

Intensity = Literal[
    "low",
    "medium",
    "high",
]

ExperienceLevel = Literal[
    "beginner",
    "intermediate",
    "advanced",
]


class UserInput(BaseModel):
    user_id: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=120,
    )

    age: int = Field(
        ...,
        ge=13,
        le=100,
    )

    weight: float = Field(
        ...,
        gt=20,
        le=400,
    )

    goal: Goal

    intensity: Intensity

    experience_level: ExperienceLevel = "beginner"

    @field_validator("name", "user_id")
    @classmethod
    def strip_strings(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty.")

        return value


class FeedbackRequest(BaseModel):
    user_id: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    feedback: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )


class WorkoutDay(BaseModel):
    day: str
    focus: str
    warm_up: list[str]
    exercises: list[str]
    cooldown: list[str]
    recovery_tip: str


class WorkoutPlan(BaseModel):
    title: str
    goal: str
    intensity: str
    safety_note: str
    days: list[WorkoutDay]


class NutritionTip(BaseModel):
    title: str
    tip: str
    practical_actions: list[str]
    disclaimer: str
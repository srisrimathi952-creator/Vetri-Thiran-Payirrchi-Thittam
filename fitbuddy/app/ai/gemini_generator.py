import json

from app.ai.gemini_client import get_gemini_client, get_structured_config
from app.config import settings
from app.schemas import WorkoutPlan


def _demo_workout_plan(
    name: str,
    goal: str,
    intensity: str,
    experience_level: str,
) -> str:
    """
    Local demo fallback.

    This allows the complete application to be tested
    without a Gemini API key.
    """

    intensity_multiplier = {
        "low": "2 sets",
        "medium": "3 sets",
        "high": "3–4 sets",
    }.get(intensity, "3 sets")

    days = [
        {
            "day": "Day 1",
            "focus": "Full Body Strength",
            "warm_up": [
                "5 minutes of easy walking",
                "Arm circles",
                "Bodyweight squats",
            ],
            "exercises": [
                f"Bodyweight squats — {intensity_multiplier}, 10–12 reps",
                f"Push-ups — {intensity_multiplier}, 8–12 reps",
                f"Glute bridges — {intensity_multiplier}, 12–15 reps",
                "Rest 60–90 seconds between sets",
            ],
            "cooldown": [
                "5 minutes gentle stretching",
            ],
            "recovery_tip": "Hydrate and allow adequate recovery before the next session.",
        },
        {
            "day": "Day 2",
            "focus": "Cardio",
            "warm_up": [
                "5 minutes easy walking",
            ],
            "exercises": [
                "Brisk walking or cycling — 20–30 minutes",
                "Keep the effort conversational",
            ],
            "cooldown": [
                "5 minutes slow walking",
                "Gentle lower-body stretching",
            ],
            "recovery_tip": "Prioritize hydration and sleep.",
        },
        {
            "day": "Day 3",
            "focus": "Upper Body",
            "warm_up": [
                "Arm circles",
                "Light mobility for shoulders",
            ],
            "exercises": [
                f"Incline push-ups — {intensity_multiplier}, 8–12 reps",
                f"Backpack rows — {intensity_multiplier}, 10–12 reps",
                f"Shoulder raises — {intensity_multiplier}, 10–15 reps",
            ],
            "cooldown": [
                "Chest and shoulder stretches",
            ],
            "recovery_tip": "Avoid training through sharp pain.",
        },
        {
            "day": "Day 4",
            "focus": "Active Recovery",
            "warm_up": [
                "5 minutes relaxed walking",
            ],
            "exercises": [
                "20–30 minutes easy walking",
                "Gentle mobility",
                "Optional beginner yoga",
            ],
            "cooldown": [
                "Relaxed breathing",
                "Gentle stretching",
            ],
            "recovery_tip": "Use this day to recover rather than maximize intensity.",
        },
        {
            "day": "Day 5",
            "focus": "Lower Body",
            "warm_up": [
                "5 minutes walking",
                "Hip mobility",
            ],
            "exercises": [
                f"Squats — {intensity_multiplier}, 10–12 reps",
                f"Reverse lunges — {intensity_multiplier}, 8–10 each side",
                f"Calf raises — {intensity_multiplier}, 12–15 reps",
            ],
            "cooldown": [
                "Quadriceps stretch",
                "Hamstring stretch",
            ],
            "recovery_tip": "Give your legs sufficient recovery before another hard session.",
        },
        {
            "day": "Day 6",
            "focus": "Core and Cardio",
            "warm_up": [
                "5 minutes easy cardio",
            ],
            "exercises": [
                f"Plank — {intensity_multiplier}, 20–40 seconds",
                f"Dead bug — {intensity_multiplier}, 8–12 each side",
                "20 minutes moderate cardio",
            ],
            "cooldown": [
                "Gentle trunk and hip stretching",
            ],
            "recovery_tip": "Keep core exercises controlled rather than rushing repetitions.",
        },
        {
            "day": "Day 7",
            "focus": "Rest and Mobility",
            "warm_up": [
                "Optional 5-minute relaxed walk",
            ],
            "exercises": [
                "Rest",
                "10–20 minutes gentle mobility if comfortable",
            ],
            "cooldown": [
                "Relaxed breathing",
            ],
            "recovery_tip": "Review how you felt during the week before progressing.",
        },
    ]

    plan = {
        "title": f"{name}'s 7-Day {goal.title()} Plan",
        "goal": goal,
        "intensity": intensity,
        "safety_note": (
            "Demo plan only. Adjust activity to your ability and stop if you "
            "experience unusual pain, dizziness, chest pain, or other concerning symptoms."
        ),
        "days": days,
    }

    return json.dumps(plan, indent=2)


def generate_workout_gemini(
    name: str,
    age: int,
    weight: float,
    goal: str,
    intensity: str,
    experience_level: str,
) -> str:
    """
    Generate a structured 7-day workout plan with Gemini.
    """

    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_workout_plan(
            name=name,
            goal=goal,
            intensity=intensity,
            experience_level=experience_level,
        )

    client = get_gemini_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key is not configured. "
            "Set GEMINI_API_KEY or enable DEMO_MODE=true."
        )

    prompt = f"""
You are FitBuddy, a fitness-planning assistant.

Create a practical 7-day fitness plan.

User profile:
- Name: {name}
- Age: {age}
- Weight: {weight} kg
- Goal: {goal}
- Preferred intensity: {intensity}
- Experience level: {experience_level}

Requirements:
1. Return exactly 7 days.
2. Each day must have:
   - day
   - focus
   - warm_up
   - exercises
   - cooldown
   - recovery_tip
3. Include exercise sets/repetitions or duration when appropriate.
4. Include rest/recovery.
5. Respect the requested intensity.
6. Do not diagnose or treat medical conditions.
7. Do not provide dangerous or extreme exercise instructions.
8. Make the plan practical for a general wellness user.
9. Include a concise safety note.
10. Return only structured JSON matching the requested schema.
"""

    config = get_structured_config(WorkoutPlan)

    response = client.models.generate_content(
        model=settings.gemini_workout_model,
        contents=prompt,
        config=config,
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty workout plan.")

    parsed = WorkoutPlan.model_validate_json(response.text)

    return parsed.model_dump_json(indent=2)
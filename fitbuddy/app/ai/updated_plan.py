import json

from app.ai.gemini_client import get_gemini_client, get_structured_config
from app.config import settings
from app.schemas import WorkoutPlan


def _demo_update_plan(
    original_plan: str,
    feedback: str,
) -> str:
    """
    Simple local fallback for testing the feedback workflow.
    """

    try:
        data = json.loads(original_plan)
    except json.JSONDecodeError:
        return original_plan

    data["feedback_applied"] = feedback

    data["safety_note"] = (
        data.get("safety_note", "")
        + " The updated plan reflects the submitted user feedback."
    ).strip()

    feedback_lower = feedback.lower()

    if "cardio" in feedback_lower:
        data["days"][1]["focus"] = "Cardio Focus"
        data["days"][5]["focus"] = "Core and Cardio"

    if "rest" in feedback_lower:
        data["days"][3]["focus"] = "Rest and Recovery"
        data["days"][3]["exercises"] = [
            "Rest",
            "Optional gentle walking",
            "Optional light mobility",
        ]

    if "yoga" in feedback_lower:
        data["days"][3]["exercises"].append(
            "10–20 minutes gentle yoga"
        )

    if "easy" in feedback_lower or "lighter" in feedback_lower:
        for day in data["days"]:
            day["recovery_tip"] = (
                "Keep the effort comfortable and prioritize recovery."
            )

    return json.dumps(data, indent=2)


def update_workout_plan(
    original_plan: str,
    feedback: str,
) -> str:
    """
    Regenerate a workout plan using the original plan and user feedback.
    """

    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_update_plan(
            original_plan=original_plan,
            feedback=feedback,
        )

    client = get_gemini_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key is not configured."
        )

    prompt = f"""
You are updating an existing FitBuddy workout plan.

Original plan:
{original_plan}

User feedback:
{feedback}

Requirements:
1. Preserve useful parts of the original plan.
2. Apply the feedback where reasonable.
3. Return exactly 7 days.
4. Keep the plan safe and practical.
5. Do not diagnose or treat medical conditions.
6. Include warm-up, exercises, cooldown, and recovery guidance.
7. Do not make extreme or unsafe recommendations.
8. Return only JSON matching the requested WorkoutPlan schema.
"""

    config = get_structured_config(WorkoutPlan)

    response = client.models.generate_content(
        model=settings.gemini_workout_model,
        contents=prompt,
        config=config,
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty updated plan.")

    parsed = WorkoutPlan.model_validate_json(response.text)

    return parsed.model_dump_json(indent=2)
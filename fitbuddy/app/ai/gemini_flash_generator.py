import json

from app.ai.gemini_client import get_gemini_client, get_structured_config
from app.config import settings
from app.schemas import NutritionTip


def _demo_nutrition_tip(goal: str) -> str:
    tips = {
        "weight loss": {
            "title": "Build balanced meals",
            "tip": "Prioritize vegetables, adequate protein, whole foods, and sensible portions.",
            "practical_actions": [
                "Include a protein source in your meals.",
                "Choose water as your main beverage.",
                "Include vegetables or fruit regularly.",
            ],
        },
        "muscle gain": {
            "title": "Support recovery with protein",
            "tip": "Include a protein-rich food regularly across the day and eat enough overall to support training.",
            "practical_actions": [
                "Include protein such as eggs, fish, beans, dairy, or lean meat.",
                "Eat a balanced meal after training.",
                "Stay adequately hydrated.",
            ],
        },
        "general wellness": {
            "title": "Focus on balanced nutrition",
            "tip": "Aim for a varied diet containing vegetables, fruit, whole grains, protein sources, and healthy fats.",
            "practical_actions": [
                "Include a variety of colorful vegetables and fruits.",
                "Choose mostly minimally processed foods.",
                "Drink water regularly.",
            ],
        },
        "flexibility": {
            "title": "Fuel consistent movement",
            "tip": "Maintain regular balanced meals and adequate hydration while working on mobility.",
            "practical_actions": [
                "Hydrate throughout the day.",
                "Include protein with meals.",
                "Eat a varied selection of whole foods.",
            ],
        },
        "endurance": {
            "title": "Support endurance training",
            "tip": "Use balanced meals containing carbohydrates, protein, fluids, and nutrient-rich foods to support activity.",
            "practical_actions": [
                "Include carbohydrate-rich whole foods around training.",
                "Hydrate before and after exercise.",
                "Include protein as part of recovery meals.",
            ],
        },
    }

    selected = tips.get(goal, tips["general wellness"])

    selected["disclaimer"] = (
        "General wellness information only; individual nutrition needs vary."
    )

    return json.dumps(selected, indent=2)


def generate_nutrition_tip_with_flash(
    goal: str,
    intensity: str,
) -> str:
    """
    Generate a concise nutrition/recovery recommendation.
    """

    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_nutrition_tip(goal)

    client = get_gemini_client()

    if client is None:
        raise RuntimeError(
            "Gemini API key is not configured."
        )

    prompt = f"""
You are a wellness nutrition assistant.

Generate one concise nutrition or recovery recommendation.

Fitness goal:
{goal}

Workout intensity:
{intensity}

Requirements:
- Keep the advice practical.
- Do not prescribe a medical diet.
- Do not diagnose medical conditions.
- Mention hydration or recovery when relevant.
- Give 2–4 practical actions.
- Return JSON matching the requested schema.
"""

    config = get_structured_config(NutritionTip)

    response = client.models.generate_content(
        model=settings.gemini_tip_model,
        contents=prompt,
        config=config,
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty nutrition tip.")

    parsed = NutritionTip.model_validate_json(response.text)

    return parsed.model_dump_json(indent=2)
"""
Guidance service.
Takes a cry classification result and generates
caring, actionable advice using Azure OpenAI.
"""
import logging
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

_client = OpenAI(
    base_url=settings.AZURE_OPENAI_ENDPOINT,
    api_key=settings.AZURE_OPENAI_KEY,
)

# Human-readable labels and base context per cry type
CRY_CONTEXT = {
    "hungry":     "The baby is hungry and needs feeding.",
    "tired":      "The baby is tired and needs to sleep.",
    "burping":    "The baby needs to be burped — trapped gas is causing discomfort.",
    "discomfort": "The baby is uncomfortable — could be clothing, temperature, or position.",
    "lonely":     "The baby is lonely and needs comfort, skin contact, or holding.",
    "scared":     "The baby is startled or scared and needs soothing reassurance.",
    "belly_pain": "The baby may have belly pain — colic, gas, or digestive discomfort.",
    "cold_hot":   "The baby may be too cold or too hot and needs temperature adjustment.",
    "unknown":    "The cry type could not be clearly identified.",
}


def generate_guidance(cry_type: str, confidence: float, child=None, mother=None) -> str:
    """
    Generate warm, practical guidance for the mother based on cry classification.
    Returns a markdown-formatted string.
    """
    cry_label   = CRY_CONTEXT.get(cry_type, "An unidentified cry type.")
    child_name  = child.name if child else "your baby"
    child_age   = child.age_display if child else "a newborn"
    mother_name = mother.first_name if mother else "Mum"
    conf_pct    = round(confidence * 100)

    prompt = f"""
You are MamaCare AI — a warm, knowledgeable newborn care assistant based in Kenya.

A mother named {mother_name} just recorded her baby {child_name}'s cry ({child_age}).
The AI classified the cry as: **{cry_type.replace('_', ' ').title()}** with {conf_pct}% confidence.
Context: {cry_label}

Write a warm, practical response to {mother_name} that:
1. Briefly confirms what the cry likely means (1-2 sentences, reassuring tone)
2. Gives 3-5 clear, actionable steps she can take RIGHT NOW
3. Mentions any warning signs that would mean she should seek medical help
4. Ends with a warm, encouraging note

Format with **bold** for key actions and use short bullet points.
Keep it concise — this is a tired new mother reading on her phone.
Do NOT repeat the confidence score or technical details.
""".strip()

    try:
        response = _client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("[GuidanceService] Azure OpenAI call failed: %s", e)
        return (
            f"Based on the cry analysis, {child_name} appears to be **{cry_type.replace('_', ' ')}**.\n\n"
            f"{cry_label}\n\n"
            "Please check on your baby and respond to their needs. "
            "If you are concerned, contact your pediatrician."
        )
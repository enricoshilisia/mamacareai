"""
AI services for the consultations app.
Reuses _client from chat/services.py.
"""
import json
import logging

from django.conf import settings

from chat.services import _client

logger = logging.getLogger(__name__)


def assess_severity(conversation) -> dict:
    """
    Sends the last 15 messages from a Conversation to the AI and asks it to
    assess: severity (mild/moderate/severe/critical), main symptoms, and
    recommended specialist type.

    Returns a dict: {severity, symptoms, specialist}
    """
    msgs = list(conversation.messages.order_by("-created_at")[:15])
    msgs.reverse()

    history = [{"role": m.role, "content": m.content} for m in msgs]

    system_prompt = (
        "You are a medical triage assistant. "
        "Based on this conversation between a mother and a care AI about her child's symptoms, assess:\n"
        "1) severity — choose ONE of: mild, moderate, severe, critical\n"
        "2) main symptoms — describe in 2-3 clear sentences\n"
        "3) recommended specialist type — choose ONE of: pediatrician, neonatologist, gp, lactation, nutritionist\n\n"
        "Return ONLY valid JSON with no markdown, no code fences, no extra text:\n"
        '{"severity": "...", "symptoms": "...", "specialist": "..."}'
    )

    try:
        response = _client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
            ],
            max_completion_tokens=400,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        # Validate and normalise
        severity = result.get("severity", "mild").lower()
        if severity not in ("mild", "moderate", "severe", "critical"):
            severity = "mild"
        specialist = result.get("specialist", "gp").lower()
        if specialist not in ("pediatrician", "neonatologist", "gp", "lactation", "nutritionist"):
            specialist = "gp"
        return {
            "severity":   severity,
            "symptoms":   result.get("symptoms", "Symptoms could not be assessed."),
            "specialist": specialist,
        }
    except Exception as exc:
        logger.exception("assess_severity failed: %s", exc)
        return {
            "severity":   "moderate",
            "symptoms":   "Unable to assess symptoms automatically. Please describe the child's condition.",
            "specialist": "pediatrician",
        }


def generate_summary(consultation) -> str:
    """
    Generates a concise clinical summary (3-5 sentences) for the doctor
    based on the linked conversation history and consultation data.

    Returns a plain-text string.
    """
    history_lines = []
    if consultation.conversation:
        msgs = list(consultation.conversation.messages.order_by("created_at"))
        history_lines = [
            f"{m.role.upper()}: {m.content}"
            for m in msgs
        ]

    child = consultation.child
    child_info = ""
    if child:
        child_info = (
            f"Patient: {child.name}, {child.age_display}, {child.gender_display}. "
        )
        if child.allergies:
            child_info += f"Known conditions/allergies: {child.allergies}. "

    history_text = "\n".join(history_lines) if history_lines else "No chat history available."

    system_prompt = (
        "You are a medical assistant preparing a handover note for a doctor. "
        "Write a concise clinical summary (3-5 sentences) about this child patient. "
        "Include: child's age and profile, main symptoms, severity level, and key context from the conversation. "
        "Be clinical and factual. Do not add disclaimers."
    )

    user_content = (
        f"{child_info}"
        f"Severity: {consultation.severity}. "
        f"Symptoms: {consultation.symptoms}\n\n"
        f"Chat history:\n{history_text}"
    )

    try:
        response = _client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            max_completion_tokens=300,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("generate_summary failed: %s", exc)
        return (
            f"Patient severity: {consultation.severity}. "
            f"Symptoms: {consultation.symptoms}"
        )

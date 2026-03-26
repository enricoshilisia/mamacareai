"""
AI services for the consultations app.
Reuses _client from chat/services.py.
"""
import json
import logging

from django.conf import settings

from chat.services import _client

logger = logging.getLogger(__name__)


def _build_child_profile(child) -> str:
    """Return a formatted profile block for a child."""
    if not child:
        return "No child profile linked to this conversation."
    lines = [
        f"Name: {child.name}",
        f"Age: {child.age_display}",
        f"Gender: {child.gender_display}",
    ]
    if child.blood_group and child.blood_group != "unknown":
        lines.append(f"Blood group: {child.blood_group}")
    if child.birth_weight_kg:
        lines.append(f"Birth weight: {child.birth_weight_kg} kg")
    if child.birth_hospital:
        lines.append(f"Born at: {child.birth_hospital}")
    if child.allergies:
        lines.append(f"Allergies / conditions: {child.allergies}")
    if child.notes:
        lines.append(f"Notes: {child.notes}")
    if child.pediatrician_name:
        lines.append(f"Regular pediatrician: {child.pediatrician_name}"
                     + (f" ({child.pediatrician_phone})" if child.pediatrician_phone else ""))
    return "\n".join(lines)


def _build_chat_history(conversation) -> str:
    """
    Return the last 30 messages of the current conversation,
    plus a brief summary (first user message) of up to 4 previous
    conversations about the same child.
    """
    from chat.models import Conversation  # local import to avoid circular

    lines = []

    # Previous conversations about the same child (most recent 4, excluding current)
    if conversation.child_id:
        past = (
            Conversation.objects
            .filter(child_id=conversation.child_id)
            .exclude(pk=conversation.pk)
            .order_by("-updated_at")[:4]
        )
        if past:
            lines.append("── Previous conversations ──")
            for pc in past:
                first_msg = pc.messages.order_by("created_at").first()
                if first_msg:
                    lines.append(f"[{pc.updated_at.strftime('%d %b %Y')}] {first_msg.content[:200]}")
            lines.append("")

    # Current conversation (last 30 messages)
    lines.append("── Current conversation ──")
    msgs = list(conversation.messages.order_by("-created_at")[:30])
    msgs.reverse()
    for m in msgs:
        role = "Mother" if m.role == "user" else "MamaCare AI"
        lines.append(f"{role}: {m.content}")

    return "\n".join(lines)


def assess_severity(conversation) -> dict:
    """
    Builds a comprehensive clinical report for the doctor using:
    - Child's full profile (age, blood group, allergies, etc.)
    - Current conversation history
    - Recent past conversations about the same child

    Returns: {severity, symptoms (full report for doctor), specialist}
    """
    child = conversation.child
    mother = conversation.mother

    child_profile = _build_child_profile(child)
    chat_history  = _build_chat_history(conversation)

    system_prompt = (
        "You are a medical triage assistant preparing a handover report for a doctor.\n\n"
        "Using the child's profile and the conversation history provided, produce:\n"
        "1. severity — ONE of: mild, moderate, severe, critical\n"
        "2. report — a structured clinical summary for the doctor in this exact format:\n"
        "   PATIENT: <name, age, gender>\n"
        "   PROFILE: <blood group, birth weight, known allergies/conditions>\n"
        "   PRESENTING CONCERN: <what the mother is worried about — 2-3 sentences>\n"
        "   HISTORY: <relevant past concerns from previous conversations, if any>\n"
        "   ASSESSMENT: <brief clinical impression and suggested next steps>\n"
        "   MOTHER: <mother's name and location>\n"
        "3. specialist — ONE of: pediatrician, neonatologist, gp, lactation, nutritionist\n\n"
        "Return ONLY valid JSON, no markdown:\n"
        '{"severity": "...", "report": "...", "specialist": "..."}'
    )

    user_content = (
        f"=== CHILD PROFILE ===\n{child_profile}\n\n"
        f"=== MOTHER ===\n{mother.full_name}, {getattr(mother, 'city', '')} {getattr(mother, 'country', '')}\n\n"
        f"=== CONVERSATION ===\n{chat_history}"
    )

    try:
        response = _client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            max_completion_tokens=800,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)

        severity = result.get("severity", "moderate").lower()
        if severity not in ("mild", "moderate", "severe", "critical"):
            severity = "moderate"
        specialist = result.get("specialist", "pediatrician").lower()
        if specialist not in ("pediatrician", "neonatologist", "gp", "lactation", "nutritionist"):
            specialist = "pediatrician"

        return {
            "severity":   severity,
            "symptoms":   result.get("report", "Clinical report could not be generated."),
            "specialist": specialist,
        }
    except Exception as exc:
        logger.exception("assess_severity failed: %s", exc)
        # Fallback: build a plain-text report without AI
        fallback = (
            f"PATIENT: {child.name if child else 'Unknown'}\n"
            f"PROFILE: {child_profile}\n"
            f"MOTHER: {mother.full_name}, {getattr(mother, 'city', '')} {getattr(mother, 'country', '')}\n"
            f"NOTE: AI assessment unavailable. Please review the conversation history."
        )
        return {
            "severity":   "moderate",
            "symptoms":   fallback,
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

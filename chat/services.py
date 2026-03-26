from django.conf import settings
from openai import OpenAI
from .models import Conversation, Message

# ── Client ────────────────────────────────────────────────────────────────────
_client = OpenAI(
    base_url=settings.AZURE_OPENAI_ENDPOINT,   # https://mcai-resource.openai.azure.com/openai/v1/
    api_key=settings.AZURE_OPENAI_KEY,
)


# ── System prompt ─────────────────────────────────────────────────────────────
def build_system_prompt(mother, child=None) -> str:
    lines = [
        "You are MamaCare AI, a warm, knowledgeable, and reassuring assistant "
        "dedicated to supporting new mothers caring for their newborns.",
        "",
        "Your role:",
        "- Answer questions about newborn care, feeding, sleep, development, and health.",
        "- Provide clear, practical, evidence-based guidance.",
        "- Be empathetic — new motherhood is overwhelming. Always acknowledge feelings first.",
        "- If a symptom sounds serious, calmly advise the mother to seek medical attention "
        "  and offer to help find a nearby doctor.",
        "- Never diagnose. Never alarm unnecessarily. Always encourage professional consultation "
        "  for anything beyond general guidance.",
        "- Keep responses concise and easy to read. Use short paragraphs.",
        "- You are based in Kenya. Be aware of local context where relevant.",
        "",
        "SPECIAL FORMAT — Crying questions:",
        "When a mother asks about her baby crying (e.g. 'why is she crying?', 'she won't "
        "stop crying'), give your normal warm, helpful response. Then on a new line at the "
        "very end, add exactly this token and nothing after it: [RECORD_CRY]",
        "Use ONLY this token for crying questions. Never use it for any other topic.",
        "",
        f"Mother's name: {mother.full_name}",
        f"Location: {mother.city or 'Kenya'}",
    ]

    if child:
        lines += [
            "",
            "─── Child context ───",
            f"Name: {child.name}",
            f"Age: {child.age_display}",
            f"Gender: {child.gender_display}",
        ]
        if child.blood_group and child.blood_group != "unknown":
            lines.append(f"Blood group: {child.blood_group}")
        if child.birth_weight_kg:
            lines.append(f"Birth weight: {child.birth_weight_kg} kg")
        if child.allergies:
            lines.append(f"Known allergies / conditions: {child.allergies}")
        if child.pediatrician_name:
            lines.append(
                f"Pediatrician: {child.pediatrician_name}"
                + (f" ({child.pediatrician_phone})" if child.pediatrician_phone else "")
            )
        lines += [
            "",
            f"Every response should keep {child.name}'s age and profile in mind.",
            f"Address the mother by her first name ({mother.first_name}) naturally.",
        ]
    else:
        lines += [
            "",
            "This is a general chat — no specific child is selected.",
            f"Address the mother as {mother.first_name}.",
        ]

    return "\n".join(lines)


# ── History builder ───────────────────────────────────────────────────────────
def build_message_history(conversation: Conversation) -> list:
    msgs = conversation.messages.order_by("-created_at")[:20]
    return [
        {"role": m.role, "content": m.content}
        for m in reversed(msgs)
    ]


# ── Main streaming function ───────────────────────────────────────────────────
def stream_ai_reply(conversation: Conversation, user_text: str):
    """
    Saves the user message, streams the AI reply chunk by chunk,
    then saves the complete assistant message.
    Yields string chunks as they arrive.
    """
    mother = conversation.mother
    child  = conversation.child

    # 1. Save user message
    Message.objects.create(
        conversation=conversation,
        role="user",
        content=user_text,
    )

    # 2. Auto-title the conversation from the first user message
    if not conversation.title:
        conversation.title = user_text[:80]
        conversation.save(update_fields=["title"])

    # 3. Build messages list
    history = build_message_history(conversation)
    messages = [
        {"role": "system", "content": build_system_prompt(mother, child)},
        *history,
    ]

    # 4. Stream from Azure
    full_reply = ""
    stream = _client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=messages,
        max_completion_tokens=1024,  # ← correct param for this model
        temperature=0.7,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            full_reply += delta.content
            yield delta.content

    # 5. Save complete assistant message
    if full_reply:
        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=full_reply,
        )
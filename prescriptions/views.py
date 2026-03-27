import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

logger = logging.getLogger(__name__)
from django.views.decorators.http import require_POST

from consultations.models import Consultation
from .models import Prescription, PrescriptionItem


def _ai_suggest_drugs(consultation):
    """Call Azure OpenAI to suggest drugs based on consultation context."""
    from django.conf import settings
    from openai import OpenAI

    child = consultation.child
    child_info = ""
    if child:
        age_days = (timezone.now().date() - child.date_of_birth).days if child.date_of_birth else None
        age_str  = f"{age_days // 7} weeks" if age_days and age_days < 84 else (f"{age_days // 30} months" if age_days else "unknown age")
        child_info = (
            f"Patient: {child.name}, {age_str} old, {child.get_gender_display()}\n"
            f"Birth weight: {child.birth_weight_kg or 'unknown'} kg\n"
            f"Blood group: {child.blood_group or 'unknown'}\n"
            f"Allergies: {child.allergies or 'none known'}\n"
        )

    symptoms = consultation.symptoms or ""
    summary  = consultation.ai_summary or ""

    recent_msgs = consultation.messages.order_by('-created_at')[:10]
    chat_lines  = "\n".join(
        f"{'Doctor' if m.sender_type == 'doctor' else 'Mother'}: {m.content}"
        for m in reversed(recent_msgs)
    )

    system_prompt = (
        "You are a paediatric clinical decision support tool used by a licensed physician "
        "during a live consultation. The doctor needs medication suggestions to review and approve. "
        "Based on the patient details and clinical context, list suitable medications.\n\n"
        "OUTPUT FORMAT — respond with ONLY a raw JSON array, no markdown, no prose, no code fences. "
        "Each object must have exactly these keys: "
        "drug_name, dosage, frequency, duration, instructions, reasoning.\n\n"
        "RULES:\n"
        "- Suggest 3-5 medications commonly used in paediatric practice for the stated symptoms.\n"
        "- Include OTC options (paracetamol, ORS, zinc) where appropriate.\n"
        "- Dosage must be weight/age appropriate.\n"
        "- If symptoms are unclear, suggest supportive care medications (ORS, paracetamol, zinc).\n"
        "- Always return at least 2 suggestions — the doctor will decide what to prescribe.\n"
        "- Never return an empty array."
    )

    user_prompt = (
        f"{child_info}\n"
        f"Clinical summary: {summary or 'Not yet summarised'}\n"
        f"Symptoms reported: {symptoms or 'Not specified'}\n"
        f"Recent consultation notes:\n{chat_lines or 'No messages yet'}"
    )

    client = OpenAI(
        base_url=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_KEY,
    )
    response = client.chat.completions.create(
        model=settings.AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.3,
        max_completion_tokens=900,
    )
    raw = response.choices[0].message.content.strip()
    logger.debug("AI drug suggestion raw response: %s", raw)

    # Strip markdown code fences if model ignores instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    result = json.loads(raw)

    # Fallback: if model returned empty array despite instruction, use ORS defaults
    if not result:
        logger.warning("AI returned empty drug list for consultation %s", consultation.pk)
        result = [
            {
                "drug_name": "Paracetamol (Calpol)",
                "dosage": "15 mg/kg per dose",
                "frequency": "Every 6 hours as needed",
                "duration": "3-5 days",
                "instructions": "Give with food. Do not exceed 4 doses in 24 hours.",
                "reasoning": "First-line antipyretic and analgesic for infants.",
            },
            {
                "drug_name": "Oral Rehydration Salts (ORS)",
                "dosage": "As needed for hydration",
                "frequency": "After each loose stool or vomiting episode",
                "duration": "Until symptoms resolve",
                "instructions": "Mix one sachet in 200ml clean water. Give small sips frequently.",
                "reasoning": "Prevents dehydration in infants with diarrhoea or fever.",
            },
            {
                "drug_name": "Zinc Sulphate",
                "dosage": "10 mg once daily (under 6 months) / 20 mg once daily (6 months+)",
                "frequency": "Once daily",
                "duration": "10-14 days",
                "instructions": "Dissolve tablet in small amount of water or breast milk.",
                "reasoning": "Reduces duration and severity of diarrhoea in children.",
            },
        ]

    return result


@login_required
@require_POST
def suggest_drugs(request, pk):
    """Return AI drug suggestions for a consultation."""
    consultation = get_object_or_404(Consultation, pk=pk)

    if not request.user.is_doctor:
        return JsonResponse({'error': 'Doctors only'}, status=403)

    try:
        drugs = _ai_suggest_drugs(consultation)
        return JsonResponse({'drugs': drugs})
    except Exception as e:
        return JsonResponse({'error': str(e), 'drugs': []}, status=200)


@login_required
@require_POST
def confirm_prescription(request, pk):
    """Save confirmed prescription and notify mother via push."""
    consultation = get_object_or_404(Consultation, pk=pk)

    if not request.user.is_doctor:
        return JsonResponse({'error': 'Doctors only'}, status=403)

    try:
        data  = json.loads(request.body)
        items = data.get('items', [])
        notes = data.get('notes', '')

        if not items:
            return JsonResponse({'error': 'No drugs provided'}, status=400)

        # Create or replace prescription
        Prescription.objects.filter(consultation=consultation).delete()
        rx = Prescription.objects.create(
            consultation=consultation,
            created_by=request.user,
            notes=notes,
            confirmed_at=timezone.now(),
        )
        for item in items:
            PrescriptionItem.objects.create(
                prescription=rx,
                drug_name=item.get('drug_name', ''),
                dosage=item.get('dosage', ''),
                frequency=item.get('frequency', ''),
                duration=item.get('duration', ''),
                instructions=item.get('instructions', ''),
                ai_suggested=item.get('ai_suggested', False),
            )

        # In-app + push notification to mother
        try:
            from notifications.services import notify_user
            child_name  = consultation.child.name if consultation.child else 'your baby'
            doctor_name = f"Dr. {consultation.physician.full_name}"
            notify_user(
                consultation.mother,
                title="Prescription Ready 💊",
                body=f"{doctor_name} has sent a prescription for {child_name}. Tap to view.",
                url=f"/consultations/{consultation.pk}/chat/",
            )
        except Exception as notify_err:
            logger.warning("Failed to send prescription notification: %s", notify_err)

        return JsonResponse({'ok': True, 'prescription_id': str(rx.pk)})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_prescription(request, pk):
    """Return prescription data for a consultation."""
    consultation = get_object_or_404(Consultation, pk=pk)
    try:
        rx = consultation.prescription
        if not rx.is_confirmed:
            return JsonResponse({'prescription': None})
        items = [
            {
                'drug_name':    i.drug_name,
                'dosage':       i.dosage,
                'frequency':    i.frequency,
                'duration':     i.duration,
                'instructions': i.instructions,
                'ai_suggested': i.ai_suggested,
            }
            for i in rx.items.all()
        ]
        return JsonResponse({
            'prescription': {
                'id':           str(rx.pk),
                'notes':        rx.notes,
                'confirmed_at': rx.confirmed_at.strftime('%d %b %Y, %H:%M'),
                'items':        items,
                'doctor':       f"Dr. {consultation.physician.full_name}",
            }
        })
    except Prescription.DoesNotExist:
        return JsonResponse({'prescription': None})

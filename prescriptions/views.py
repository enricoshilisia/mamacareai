import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
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
            f"Birth weight: {child.birth_weight or 'unknown'}\n"
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
        "You are a clinical decision support assistant for paediatric care. "
        "Based on the patient information and clinical context provided, suggest appropriate medications. "
        "Return ONLY a valid JSON array. No prose, no markdown, no code fences. "
        "Each item must have exactly these fields: "
        "drug_name, dosage, frequency, duration, instructions, reasoning. "
        "Dosage must be weight/age appropriate for the child. "
        "Limit to 5 drugs maximum. Only suggest medications appropriate for infants/children."
    )

    user_prompt = (
        f"{child_info}\n"
        f"Clinical summary: {summary}\n"
        f"Symptoms: {symptoms}\n"
        f"Recent conversation:\n{chat_lines}"
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
        temperature=0.2,
        max_tokens=800,
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


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

        # Push notification to mother
        try:
            from notifications.services import send_push_to_user
            child_name = consultation.child.name if consultation.child else 'your baby'
            doctor_name = f"Dr. {consultation.physician.full_name}"
            send_push_to_user(
                consultation.mother,
                title="Prescription Ready",
                body=f"{doctor_name} has sent a prescription for {child_name}. Tap to view.",
                url=f"/consultations/{consultation.pk}/chat/",
            )
        except Exception:
            pass

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

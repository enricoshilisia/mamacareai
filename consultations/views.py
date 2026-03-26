import json
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from chat.models import Conversation
from physicians.models import Physician

from .models import Consultation, ConsultationMessage
from .services import assess_severity, generate_summary


# ── Helpers ───────────────────────────────────────────────────────────────────

def _severity_order(s):
    return {"mild": 0, "moderate": 1, "severe": 2, "critical": 3}.get(s, 0)


def _find_doctors(specialist, lat=None, lon=None, mother_city=None):
    """Return up to 3 suitable doctors, sorted by distance or city match."""
    qs = Physician.objects.filter(status="approved", is_available=True)
    if specialist:
        qs = qs.filter(specialization=specialist)
    doctors = list(qs)

    if lat is not None and lon is not None:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            doctors.sort(key=lambda d: d.distance_from(lat_f, lon_f))
        except (ValueError, TypeError):
            pass
    elif mother_city:
        city_lower = mother_city.lower()
        doctors.sort(key=lambda d: (0 if d.city.lower() == city_lower else 1, d.full_name))

    return doctors[:3]


# ── Mother-facing views ────────────────────────────────────────────────────────

# Cry type → (severity, specialist)
_CRY_SEVERITY = {
    "hungry":     ("mild",     "pediatrician"),
    "tired":      ("mild",     "pediatrician"),
    "burping":    ("mild",     "pediatrician"),
    "lonely":     ("mild",     "pediatrician"),
    "cold_hot":   ("mild",     "pediatrician"),
    "discomfort": ("moderate", "pediatrician"),
    "belly_pain": ("moderate", "pediatrician"),
    "scared":     ("moderate", "pediatrician"),
}


@login_required
def assess_cry(request):
    """
    GET consultations/assess-cry/?cry_type=...&lat=...&lon=...&child_id=...
    Returns doctors near the mother based on cry analysis result.
    """
    cry_type   = request.GET.get("cry_type", "")
    lat        = request.GET.get("lat")
    lon        = request.GET.get("lon")
    child_id   = request.GET.get("child_id", "")

    severity, specialist = _CRY_SEVERITY.get(cry_type, ("moderate", "pediatrician"))
    symptoms = f"Baby cry analysis result: {cry_type.replace('_', ' ').title()}. Mother is seeking guidance."

    mother  = request.user
    doctors = _find_doctors(specialist, lat=lat, lon=lon, mother_city=getattr(mother, "city", None))

    doctors_data = []
    for d in doctors:
        dist = None
        if lat and lon:
            try:
                dist = round(d.distance_from(float(lat), float(lon)), 1)
            except (ValueError, TypeError):
                pass
        doctors_data.append({
            "id":             str(d.id),
            "name":           d.full_name,
            "specialization": d.get_specialization_display(),
            "hospital":       d.hospital,
            "city":           d.city,
            "distance_km":    dist,
        })

    return JsonResponse({
        "severity":   severity,
        "symptoms":   symptoms,
        "specialist": specialist,
        "doctors":    doctors_data,
        "conv_id":    "",
        "child_id":   child_id,
    })


@login_required
def assess(request, conv_id):
    """
    GET consultations/assess/<conv_id>/?lat=...&lon=...
    Assess severity from conversation and return JSON with top doctors.
    """
    conv = get_object_or_404(Conversation, id=conv_id, mother=request.user)

    result = assess_severity(conv)
    severity  = result["severity"]
    symptoms  = result["symptoms"]
    specialist = result["specialist"]

    # Only suggest doctors if moderate or above
    doctors_data = []
    if _severity_order(severity) >= 1:  # moderate+
        lat = request.GET.get("lat")
        lon = request.GET.get("lon")
        mother = request.user
        doctors = _find_doctors(specialist, lat=lat, lon=lon, mother_city=getattr(mother, "city", None))

        for d in doctors:
            dist = None
            if lat and lon:
                try:
                    dist = round(d.distance_from(float(lat), float(lon)), 1)
                except (ValueError, TypeError):
                    pass
            doctors_data.append({
                "id":             str(d.id),
                "name":           d.full_name,
                "specialization": d.get_specialization_display(),
                "hospital":       d.hospital,
                "city":           d.city,
                "distance_km":    dist,
            })

    return JsonResponse({
        "severity":   severity,
        "symptoms":   symptoms,
        "specialist": specialist,
        "doctors":    doctors_data,
        "conv_id":    str(conv_id),
        "child_id":   str(conv.child_id) if conv.child_id else "",
    })


@login_required
@require_POST
def request_consultation(request):
    """
    POST consultations/request/
    Body (form): physician_id, conv_id, symptoms, severity, specialist, child_id (optional), lat, lon
    Creates a Consultation and redirects to waiting page.
    """
    physician_id = request.POST.get("physician_id")
    conv_id      = request.POST.get("conv_id")
    symptoms     = request.POST.get("symptoms", "")
    severity     = request.POST.get("severity", "moderate")
    specialist   = request.POST.get("specialist", "")
    child_id     = request.POST.get("child_id") or None
    lat          = request.POST.get("lat") or None
    lon          = request.POST.get("lon") or None

    physician = get_object_or_404(Physician, id=physician_id, status="approved")
    mother    = request.user

    conversation = None
    if conv_id:
        try:
            conversation = Conversation.objects.get(id=conv_id, mother=mother)
        except Conversation.DoesNotExist:
            pass

    child = None
    if child_id:
        try:
            from mothers.models import Child
            child = Child.objects.get(id=child_id, mother=mother)
        except Exception:
            pass

    # If no child from request, use conversation's child
    if child is None and conversation and conversation.child:
        child = conversation.child

    consultation = Consultation.objects.create(
        mother=mother,
        physician=physician,
        child=child,
        conversation=conversation,
        symptoms=symptoms,
        severity=severity,
        specialist=specialist,
        status="pending",
        mother_lat=lat if lat else None,
        mother_lon=lon if lon else None,
    )

    # Notify the doctor via Web Push
    try:
        from notifications.services import send_push_to_user
        child_name = child.name if child else "a baby"
        send_push_to_user(
            physician.user,
            title="New Consultation Request 🩺",
            body=f"{mother.first_name} needs help with {child_name}. Tap to respond.",
            url="/consultations/inbox/",
        )
    except Exception:
        pass

    return redirect("consultations:waiting", pk=consultation.pk)


@login_required
def waiting(request, pk):
    """GET consultations/<pk>/waiting/ — Mother waits for doctor response."""
    consultation = get_object_or_404(Consultation, pk=pk, mother=request.user)
    return render(request, "consultations/waiting.html", {
        "consultation": consultation,
    })


@login_required
def chat_room(request, pk):
    """GET consultations/<pk>/chat/ — Chat room for mother or doctor."""
    user = request.user

    if user.is_doctor:
        physician = get_object_or_404(
            Physician, user=user, consultations__pk=pk
        )
        consultation = get_object_or_404(
            Consultation, pk=pk, physician=physician, status="accepted"
        )
        base_template = "physicians/base.html"
        viewer = "doctor"
    else:
        consultation = get_object_or_404(
            Consultation, pk=pk, mother=user, status="accepted"
        )
        base_template = "mothers/base.html"
        viewer = "mother"

    messages = consultation.messages.order_by("created_at")
    return render(request, "consultations/chat_room.html", {
        "consultation":  consultation,
        "messages":      messages,
        "base_template": base_template,
        "viewer":        viewer,
    })


@login_required
@require_POST
def send_message(request, pk):
    """POST consultations/<pk>/message/ — Send a message in the consultation chat."""
    user = request.user

    if user.is_doctor:
        physician = get_object_or_404(Physician, user=user)
        consultation = get_object_or_404(
            Consultation, pk=pk, physician=physician, status="accepted"
        )
        sender_type = "doctor"
    else:
        consultation = get_object_or_404(
            Consultation, pk=pk, mother=user, status="accepted"
        )
        sender_type = "mother"

    try:
        body    = json.loads(request.body)
        content = body.get("content", "").strip()
    except (json.JSONDecodeError, AttributeError):
        content = request.POST.get("content", "").strip()

    if not content:
        return JsonResponse({"error": "Empty message"}, status=400)

    msg = ConsultationMessage.objects.create(
        consultation=consultation,
        sender_type=sender_type,
        content=content,
    )

    return JsonResponse({
        "ok":          True,
        "sender_type": msg.sender_type,
        "content":     msg.content,
        "created_at":  msg.created_at.isoformat(),
        "time":        msg.created_at.strftime("%H:%M"),
    })


@login_required
def poll_messages(request, pk):
    """
    GET consultations/<pk>/poll/?after=<iso_timestamp>
    Returns new messages since the given timestamp.
    """
    user = request.user

    if user.is_doctor:
        physician = get_object_or_404(Physician, user=user)
        consultation = get_object_or_404(Consultation, pk=pk, physician=physician)
    else:
        consultation = get_object_or_404(Consultation, pk=pk, mother=user)

    after_str = request.GET.get("after", "")
    qs = consultation.messages.order_by("created_at")

    if after_str:
        try:
            after_dt = datetime.fromisoformat(after_str.replace("Z", "+00:00"))
            qs = qs.filter(created_at__gt=after_dt)
        except ValueError:
            pass

    msgs = [
        {
            "sender_type": m.sender_type,
            "content":     m.content,
            "created_at":  m.created_at.isoformat(),
            "time":        m.created_at.strftime("%H:%M"),
        }
        for m in qs
    ]

    return JsonResponse({
        "messages":          msgs,
        "consultation_status": consultation.status,
    })


# ── Doctor-facing views ───────────────────────────────────────────────────────

@login_required
def inbox(request):
    """GET consultations/inbox/ — Doctor sees all their consultations."""
    if not request.user.is_doctor:
        return redirect("mothers:home")

    physician = get_object_or_404(Physician, user=request.user)
    pending   = Consultation.objects.filter(physician=physician, status="pending").order_by("-created_at")
    active    = Consultation.objects.filter(physician=physician, status="accepted").order_by("-updated_at")
    history   = Consultation.objects.filter(
        physician=physician, status__in=["declined", "completed"]
    ).order_by("-updated_at")[:20]

    return render(request, "consultations/doctor_inbox.html", {
        "physician": physician,
        "pending":   pending,
        "active":    active,
        "history":   history,
    })


@login_required
@require_POST
def respond(request, pk):
    """
    POST consultations/<pk>/respond/
    Body: action=accept|decline
    On accept: generate AI summary and redirect to chat room.
    On decline: redirect to inbox.
    """
    if not request.user.is_doctor:
        return JsonResponse({"error": "Forbidden"}, status=403)

    physician    = get_object_or_404(Physician, user=request.user)
    consultation = get_object_or_404(Consultation, pk=pk, physician=physician, status="pending")

    action = request.POST.get("action", "")

    if action == "accept":
        summary = generate_summary(consultation)
        consultation.ai_summary = summary
        consultation.status     = "accepted"
        consultation.save(update_fields=["ai_summary", "status", "updated_at"])
        return redirect("consultations:chat_room", pk=consultation.pk)

    elif action == "decline":
        consultation.status = "declined"
        consultation.save(update_fields=["status", "updated_at"])
        return redirect("consultations:inbox")

    return redirect("consultations:inbox")


@login_required
def pending_count(request):
    """GET consultations/pending-count/ — Returns pending + active counts for the sidebar badge."""
    if not request.user.is_doctor:
        return JsonResponse({"pending": 0, "active": 0})
    try:
        physician = request.user.physician_profile
        p = Consultation.objects.filter(physician=physician, status="pending").count()
        a = Consultation.objects.filter(physician=physician, status="accepted").count()
    except Exception:
        p = a = 0
    return JsonResponse({"pending": p, "active": a})


@login_required
@require_POST
def complete(request, pk):
    """POST consultations/<pk>/complete/ — Doctor marks consultation as completed."""
    if not request.user.is_doctor:
        return JsonResponse({"error": "Forbidden"}, status=403)

    physician    = get_object_or_404(Physician, user=request.user)
    consultation = get_object_or_404(Consultation, pk=pk, physician=physician, status="accepted")
    consultation.status = "completed"
    consultation.save(update_fields=["status", "updated_at"])
    return redirect("consultations:inbox")

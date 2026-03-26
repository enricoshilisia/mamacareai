import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import CryAnalysis
from .classifier_service import classify_audio
from .guidance_service import generate_guidance


@login_required
def cry_analyser(request):
    mother   = request.user
    children = mother.children.filter(is_active=True)

    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        child_pk   = request.POST.get("child_id")
        child      = None

        if not audio_file:
            messages.error(request, "Please upload an audio file.")
            return redirect("predictions:cry_analyser")

        allowed = [".wav", ".mp3", ".m4a", ".ogg", ".webm"]
        ext = os.path.splitext(audio_file.name)[1].lower()
        if ext not in allowed:
            messages.error(request, f"Unsupported file type.")
            return redirect("predictions:cry_analyser")

        if child_pk:
            from mothers.models import Child
            try:
                child = Child.objects.get(pk=child_pk, mother=mother, is_active=True)
            except Child.DoesNotExist:
                pass

        analysis = CryAnalysis.objects.create(mother=mother, child=child, audio_file=audio_file)
        result   = classify_audio(analysis.audio_file.path)

        if result["success"]:
            analysis.cry_type          = result["cry_type"]
            analysis.confidence        = result["confidence"]
            analysis.all_probabilities = result["all_probs"]
            analysis.is_serious        = result["is_serious"]
            analysis.guidance = generate_guidance(
                cry_type=result["cry_type"], confidence=result["confidence"],
                child=child, mother=mother,
            )
            analysis.save()
        else:
            analysis.cry_type = "unknown"
            analysis.guidance = "The cry analyser model is still being set up. Please check back soon."
            analysis.save()
            messages.warning(request, f"Classification note: {result.get('error', 'Model not ready')}")

        return redirect("predictions:cry_result", pk=analysis.pk)

    selected_child = None
    if children.count() == 1:
        selected_child = children.first()

    return render(request, "predictions/cry_analyser.html", {
        "children": children, "selected_child": selected_child,
    })


@login_required
def cry_result(request, pk):
    analysis = get_object_or_404(CryAnalysis, pk=pk, mother=request.user)
    return render(request, "predictions/cry_result.html", {
        "analysis": analysis, "child": analysis.child,
    })


@login_required
def cry_history(request):
    analyses = CryAnalysis.objects.filter(mother=request.user).order_by("-created_at")[:50]
    return render(request, "predictions/cry_history.html", {"analyses": analyses})


# ── AJAX — called from chat page ──────────────────────────────────────────────
@login_required
@require_POST
def cry_analyse_ajax(request):
    """Receives audio from chat, returns JSON result."""
    mother     = request.user
    audio_file = request.FILES.get("audio_file")
    child_pk   = request.POST.get("child_id")
    child      = None

    if not audio_file:
        return JsonResponse({"error": "No audio file"}, status=400)

    if child_pk:
        from mothers.models import Child
        try:
            child = Child.objects.get(pk=child_pk, mother=mother, is_active=True)
        except Child.DoesNotExist:
            pass

    analysis = CryAnalysis.objects.create(mother=mother, child=child, audio_file=audio_file)
    result   = classify_audio(analysis.audio_file.path)

    if result["success"]:
        analysis.cry_type          = result["cry_type"]
        analysis.confidence        = result["confidence"]
        analysis.all_probabilities = result["all_probs"]
        analysis.is_serious        = result["is_serious"]
        guidance = generate_guidance(
            cry_type=result["cry_type"], confidence=result["confidence"],
            child=child, mother=mother,
        )
        analysis.guidance = guidance
        analysis.save()

        from django.urls import reverse
        return JsonResponse({
            "success":    True,
            "cry_type":   result["cry_type"],
            "confidence": round(result["confidence"] * 100),
            "guidance":   guidance,
            "is_serious": result["is_serious"],
            "result_url": reverse("predictions:cry_result", kwargs={"pk": analysis.pk}),
        })

    analysis.cry_type = "unknown"
    analysis.guidance = "Could not classify. Please try again."
    analysis.save()
    return JsonResponse({"success": False, "error": result.get("error", "Failed")}, status=500)
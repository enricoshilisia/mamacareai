import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import PushSubscription


@login_required
@require_POST
def subscribe(request):
    try:
        data     = json.loads(request.body)
        endpoint = data.get("endpoint", "")
        p256dh   = data.get("keys", {}).get("p256dh", "")
        auth     = data.get("keys", {}).get("auth", "")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not endpoint:
        return JsonResponse({"error": "Missing endpoint"}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"user": request.user, "p256dh": p256dh, "auth": auth},
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def unsubscribe(request):
    try:
        data     = json.loads(request.body)
        endpoint = data.get("endpoint", "")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
    return JsonResponse({"ok": True})

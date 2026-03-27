import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import PushSubscription, InAppNotification


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


@login_required
def list_notifications(request):
    """GET /push/notifications/ — returns latest 30 in-app notifications for the current user."""
    qs = InAppNotification.objects.filter(user=request.user)[:30]
    unread = InAppNotification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({
        "unread": unread,
        "notifications": [
            {
                "id":         n.id,
                "title":      n.title,
                "body":       n.body,
                "url":        n.url,
                "is_read":    n.is_read,
                "created_at": n.created_at.strftime("%d %b, %H:%M"),
            }
            for n in qs
        ],
    })


@login_required
@require_POST
def mark_all_read(request):
    """POST /push/notifications/read/ — marks all notifications as read."""
    InAppNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})

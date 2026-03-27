import json
import logging

from django.conf import settings
from pywebpush import webpush, WebPushException

from .models import PushSubscription, InAppNotification

logger = logging.getLogger(__name__)


def send_push_to_user(user, title: str, body: str, url: str = "/"):
    """Send a Web Push notification to all of a user's subscribed devices."""
    subscriptions = PushSubscription.objects.filter(user=user)
    if not subscriptions.exists():
        return

    payload = json.dumps({"title": title, "body": body, "url": url})
    stale   = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub.as_dict(),
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                stale.append(sub.pk)
            else:
                resp_text = e.response.text if e.response is not None else "no response"
                resp_status = e.response.status_code if e.response is not None else "?"
                logger.error(
                    "Push failed for sub %s — HTTP %s: %s | key_prefix=%s",
                    sub.pk, resp_status, resp_text,
                    settings.VAPID_PRIVATE_KEY[:40] if settings.VAPID_PRIVATE_KEY else "MISSING",
                )
        except Exception as e:
            logger.error("Push error for sub %s: %s", sub.pk, e)

    if stale:
        PushSubscription.objects.filter(pk__in=stale).delete()


def notify_user(user, title: str, body: str, url: str = "/"):
    """Create an in-app notification AND send a push notification."""
    InAppNotification.objects.create(user=user, title=title, body=body, url=url)
    send_push_to_user(user, title=title, body=body, url=url)

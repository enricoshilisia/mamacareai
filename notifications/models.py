from django.db import models


class InAppNotification(models.Model):
    user       = models.ForeignKey(
        'mothers.Mother', on_delete=models.CASCADE,
        related_name='in_app_notifications',
    )
    title      = models.CharField(max_length=200)
    body       = models.TextField(blank=True)
    url        = models.CharField(max_length=500, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} → {self.user}"


class PushSubscription(models.Model):
    user     = models.ForeignKey(
        'mothers.Mother',
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
    )
    endpoint = models.TextField(unique=True)
    p256dh   = models.TextField()
    auth     = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def as_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }

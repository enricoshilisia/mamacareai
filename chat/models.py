from django.db import models
import uuid


class Conversation(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mother     = models.ForeignKey("mothers.Mother", on_delete=models.CASCADE, related_name="conversations")
    child      = models.ForeignKey(
                    "mothers.Child", on_delete=models.SET_NULL,
                    null=True, blank=True, related_name="conversations",
                    help_text="Null = general chat"
                 )
    title      = models.CharField(max_length=255, blank=True, help_text="Auto-generated from first message")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        label = self.child.name if self.child else "General"
        return f"[{label}] {self.title or 'New conversation'} — {self.mother}"


class Message(models.Model):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content      = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
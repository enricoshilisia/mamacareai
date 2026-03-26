from django.contrib import admin
from .models import Consultation, ConsultationMessage


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display  = ("id", "mother", "physician", "child", "severity", "status", "created_at")
    list_filter   = ("status", "severity", "specialist")
    search_fields = ("mother__full_name", "physician__full_name", "symptoms")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering      = ("-created_at",)


@admin.register(ConsultationMessage)
class ConsultationMessageAdmin(admin.ModelAdmin):
    list_display  = ("consultation", "sender_type", "short_content", "created_at")
    list_filter   = ("sender_type",)
    search_fields = ("content",)
    readonly_fields = ("id", "created_at")
    ordering      = ("-created_at",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:50]

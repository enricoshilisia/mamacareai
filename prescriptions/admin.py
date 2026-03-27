from django.contrib import admin
from .models import Prescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display  = ['consultation', 'created_by', 'confirmed_at', 'created_at']
    inlines       = [PrescriptionItemInline]

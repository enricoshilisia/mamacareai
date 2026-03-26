from django import forms
from .models import PhysicianReview, PhysicianRegistrationRequest


class PhysicianReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} star{'s' if i > 1 else ''}") for i in range(1, 6)],
        widget=forms.RadioSelect,
        label="Your Rating"
    )

    class Meta:
        model  = PhysicianReview
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Share your experience with this doctor (optional)..."
            })
        }


class PhysicianRegistrationForm(forms.ModelForm):
    class Meta:
        model  = PhysicianRegistrationRequest
        fields = [
            "full_name", "specialization", "hospital",
            "phone", "email", "city", "bio",
            "license_number", "notes"
        ]
        widgets = {
            "full_name":      forms.TextInput(attrs={"placeholder": "Dr. Jane Kamau"}),
            "hospital":       forms.TextInput(attrs={"placeholder": "e.g. Kenyatta National Hospital"}),
            "phone":          forms.TextInput(attrs={"placeholder": "+254 700 000 000", "type": "tel"}),
            "email":          forms.EmailInput(attrs={"placeholder": "doctor@hospital.com"}),
            "city":           forms.TextInput(attrs={"placeholder": "e.g. Nairobi"}),
            "license_number": forms.TextInput(attrs={"placeholder": "Medical license / registration number"}),
            "bio":            forms.Textarea(attrs={"rows": 3, "placeholder": "Brief professional bio..."}),
            "notes":          forms.Textarea(attrs={"rows": 2, "placeholder": "Anything else you'd like us to know..."}),
        }
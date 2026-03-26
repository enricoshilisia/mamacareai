from django import forms
from django.core.validators import RegexValidator
from .models import Mother, Child


phone_validator = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Enter a valid phone number (e.g. +254712345678)"
)


class MotherStep1Form(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Your full name", "autocomplete": "name"}),
        label="Full Name",
    )
    phone_number = forms.CharField(
        max_length=20,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={"placeholder": "+254712345678", "type": "tel"}),
        label="Phone Number",
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "your@email.com (optional)"}),
        label="Email (optional)",
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Create a password"}),
        label="Password",
        min_length=6,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm your password"}),
        label="Confirm Password",
    )

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]
        if Mother.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data


class MotherStep2Form(forms.Form):
    RELATIONSHIP_CHOICES = [
        ("", "Select relationship"),
        ("spouse", "Spouse / Partner"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("friend", "Friend"),
        ("other", "Other"),
    ]

    emergency_contact_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Jane Wanjiru"}),
        label="Emergency Contact Name",
    )
    emergency_contact_phone = forms.CharField(
        max_length=20,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={"placeholder": "+254712345678", "type": "tel"}),
        label="Emergency Contact Phone",
    )
    emergency_contact_relationship = forms.ChoiceField(
        choices=RELATIONSHIP_CHOICES,
        required=False,
        label="Relationship",
    )


class MotherStep3Form(forms.Form):
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Nairobi"}),
        label="City / Town",
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        initial="Kenya",
        widget=forms.TextInput(attrs={"placeholder": "Kenya"}),
        label="Country",
    )


class LoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "+254712345678", "type": "tel"}),
        label="Phone Number",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Your password"}),
        label="Password",
    )


class ChildForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date of Birth",
    )

    class Meta:
        model = Child
        fields = [
            "name", "date_of_birth", "gender", "photo",
            "blood_group", "birth_weight_kg", "birth_hospital",
            "pediatrician_name", "pediatrician_phone",
            "allergies", "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Baby's name"}),
            "birth_hospital": forms.TextInput(attrs={"placeholder": "e.g. Kenyatta National Hospital"}),
            "pediatrician_name": forms.TextInput(attrs={"placeholder": "Doctor's name"}),
            "pediatrician_phone": forms.TextInput(attrs={"placeholder": "+254...", "type": "tel"}),
            "allergies": forms.Textarea(attrs={"rows": 2, "placeholder": "Any known allergies or conditions..."}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Anything else to note..."}),
            "birth_weight_kg": forms.NumberInput(attrs={"placeholder": "e.g. 3.2", "step": "0.01"}),
        }

# forms.py
class ChildBasicForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['name', 'date_of_birth', 'gender', 'photo']

class ChildHealthForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['blood_group', 'birth_weight_kg', 'birth_hospital', 'pediatrician_name', 'pediatrician_phone']

class ChildNotesForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['allergies', 'notes']
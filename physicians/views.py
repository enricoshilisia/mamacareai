from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from mothers.models import Mother
from .models import Physician, PhysicianReview, PhysicianRegistrationRequest
from .forms import PhysicianReviewForm, PhysicianRegistrationForm


def _base(request):
    """Return the right base template depending on whether user is a doctor."""
    return "physicians/base.html" if getattr(request.user, "is_doctor", False) else "mothers/base.html"


# ── Doctor dashboard ──────────────────────────────────────────────────────────
@login_required
def physician_home(request):
    physician = getattr(request.user, "physician_profile", None)
    reviews   = physician.reviews.filter(is_approved=True).order_by("-created_at")[:5] if physician else []

    stats = {}
    if physician:
        qs = physician.consultations.all()
        total      = qs.count()
        completed  = qs.filter(status="completed").count()
        pending    = qs.filter(status="pending").count()
        active     = qs.filter(status="accepted").count()
        this_month = qs.filter(created_at__month=timezone.now().month,
                               created_at__year=timezone.now().year).count()
        last_month_date = timezone.now().replace(day=1) - timedelta(days=1)
        last_month = qs.filter(created_at__month=last_month_date.month,
                               created_at__year=last_month_date.year).count()

        # Severity breakdown (completed only)
        severity_qs = qs.filter(status="completed").values("severity").annotate(n=Count("id"))
        severity_map = {s["severity"]: s["n"] for s in severity_qs}

        stats = {
            "total":      total,
            "completed":  completed,
            "pending":    pending,
            "active":     active,
            "this_month": this_month,
            "last_month": last_month,
            "mild":       severity_map.get("mild", 0),
            "moderate":   severity_map.get("moderate", 0),
            "severe":     severity_map.get("severe", 0),
            "critical":   severity_map.get("critical", 0),
        }

    return render(request, "physicians/physician_home.html", {
        "physician": physician,
        "reviews":   reviews,
        "stats":     stats,
    })


# ── Directory — list all approved physicians ─────────────────────────────────
@login_required
def physician_list(request):
    physicians = Physician.objects.filter(status="approved", is_available=True)

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        physicians = physicians.filter(
            Q(full_name__icontains=q) |
            Q(hospital__icontains=q) |
            Q(city__icontains=q)
        )

    # Filter by specialization
    spec = request.GET.get("spec", "")
    if spec:
        physicians = physicians.filter(specialization=spec)

    # Sort by distance if mother has location
    mother = request.user
    lat    = request.GET.get("lat") or (mother.latitude if hasattr(mother, 'latitude') else None)
    lon    = request.GET.get("lon") or (mother.longitude if hasattr(mother, 'longitude') else None)

    physician_list_data = list(physicians)

    if lat and lon:
        try:
            lat, lon = float(lat), float(lon)
            physician_list_data.sort(key=lambda p: p.distance_from(lat, lon))
            for p in physician_list_data:
                p.distance_km = round(p.distance_from(lat, lon), 1)
        except (ValueError, TypeError):
            pass

    specializations = Physician.SPECIALIZATION_CHOICES

    return render(request, "physicians/physician_list.html", {
        "physicians":      physician_list_data,
        "specializations": specializations,
        "selected_spec":   spec,
        "search_query":    q,
        "base_template":   _base(request),
    })


# ── Physician detail ──────────────────────────────────────────────────────────
@login_required
def physician_detail(request, pk):
    physician = get_object_or_404(Physician, pk=pk, status="approved")
    reviews   = physician.reviews.filter(is_approved=True).order_by("-created_at")

    # Check if mother already reviewed
    mother          = request.user
    existing_review = reviews.filter(mother=mother).first()
    review_form     = None

    if not existing_review:
        review_form = PhysicianReviewForm(request.POST or None)
        if request.method == "POST" and review_form.is_valid():
            review = review_form.save(commit=False)
            review.physician = physician
            review.mother    = mother
            review.save()
            messages.success(request, f"Thank you for reviewing Dr. {physician.full_name}!")
            return redirect("physicians:physician_detail", pk=physician.pk)

    return render(request, "physicians/physician_detail.html", {
        "physician":       physician,
        "reviews":         reviews,
        "existing_review": existing_review,
        "review_form":     review_form,
        "base_template":   _base(request),
    })


# ── Doctor self-registration (3 steps) ───────────────────────────────────────

def physician_register_step1(request):
    """Step 1: Personal details — name, phone, email, password."""
    if request.method == "POST":
        data = {
            "full_name": request.POST.get("full_name", "").strip(),
            "phone":     request.POST.get("phone", "").strip(),
            "email":     request.POST.get("email", "").strip(),
        }
        pw1 = request.POST.get("password1", "")
        pw2 = request.POST.get("password2", "")
        errors = {}
        if not data["full_name"]:
            errors["full_name"] = "Full name is required."
        if not data["phone"]:
            errors["phone"] = "Phone number is required."
        if not data["email"]:
            errors["email"] = "Email address is required."
        if len(pw1) < 6:
            errors["password1"] = "Password must be at least 6 characters."
        elif pw1 != pw2:
            errors["password2"] = "Passwords do not match."
        if Mother.objects.filter(phone_number=data["phone"]).exists():
            errors["phone"] = "An account with this phone number already exists."
        if not errors:
            data["password"] = pw1
            request.session["dr_step1"] = data
            return redirect("physicians:physician_register_step2")
        return render(request, "physicians/register_step1.html", {"data": data, "errors": errors, "step": 1})

    return render(request, "physicians/register_step1.html", {
        "data": request.session.get("dr_step1", {}),
        "errors": {},
        "step": 1,
    })


WORLD_COUNTRIES = [
    "Afghanistan","Albania","Algeria","Andorra","Angola","Antigua and Barbuda","Argentina","Armenia",
    "Australia","Austria","Azerbaijan","Bahamas","Bahrain","Bangladesh","Barbados","Belarus","Belgium",
    "Belize","Benin","Bhutan","Bolivia","Bosnia and Herzegovina","Botswana","Brazil","Brunei","Bulgaria",
    "Burkina Faso","Burundi","Cabo Verde","Cambodia","Cameroon","Canada","Central African Republic","Chad",
    "Chile","China","Colombia","Comoros","Congo","Costa Rica","Croatia","Cuba","Cyprus","Czech Republic",
    "Denmark","Djibouti","Dominica","Dominican Republic","Ecuador","Egypt","El Salvador","Equatorial Guinea",
    "Eritrea","Estonia","Eswatini","Ethiopia","Fiji","Finland","France","Gabon","Gambia","Georgia","Germany",
    "Ghana","Greece","Grenada","Guatemala","Guinea","Guinea-Bissau","Guyana","Haiti","Honduras","Hungary",
    "Iceland","India","Indonesia","Iran","Iraq","Ireland","Israel","Italy","Jamaica","Japan","Jordan",
    "Kazakhstan","Kenya","Kiribati","Kuwait","Kyrgyzstan","Laos","Latvia","Lebanon","Lesotho","Liberia",
    "Libya","Liechtenstein","Lithuania","Luxembourg","Madagascar","Malawi","Malaysia","Maldives","Mali",
    "Malta","Marshall Islands","Mauritania","Mauritius","Mexico","Micronesia","Moldova","Monaco","Mongolia",
    "Montenegro","Morocco","Mozambique","Myanmar","Namibia","Nauru","Nepal","Netherlands","New Zealand",
    "Nicaragua","Niger","Nigeria","North Korea","North Macedonia","Norway","Oman","Pakistan","Palau",
    "Palestine","Panama","Papua New Guinea","Paraguay","Peru","Philippines","Poland","Portugal","Qatar",
    "Romania","Russia","Rwanda","Saint Kitts and Nevis","Saint Lucia","Saint Vincent and the Grenadines",
    "Samoa","San Marino","Sao Tome and Principe","Saudi Arabia","Senegal","Serbia","Seychelles",
    "Sierra Leone","Singapore","Slovakia","Slovenia","Solomon Islands","Somalia","South Africa",
    "South Korea","South Sudan","Spain","Sri Lanka","Sudan","Suriname","Sweden","Switzerland","Syria",
    "Taiwan","Tajikistan","Tanzania","Thailand","Timor-Leste","Togo","Tonga","Trinidad and Tobago",
    "Tunisia","Turkey","Turkmenistan","Tuvalu","Uganda","Ukraine","United Arab Emirates","United Kingdom",
    "United States","Uruguay","Uzbekistan","Vanuatu","Vatican City","Venezuela","Vietnam","Yemen",
    "Zambia","Zimbabwe",
]


def physician_register_step2(request):
    """Step 2: Professional details — specialization, hospital, country, city, license."""
    if "dr_step1" not in request.session:
        return redirect("physicians:physician_register")

    specializations = PhysicianRegistrationRequest._meta.get_field("specialization").choices

    if request.method == "POST":
        data = {
            "specialization": request.POST.get("specialization", "").strip(),
            "hospital":       request.POST.get("hospital", "").strip(),
            "country":        request.POST.get("country", "").strip(),
            "city":           request.POST.get("city", "").strip(),
            "license_number": request.POST.get("license_number", "").strip(),
        }
        errors = {}
        if not data["specialization"]:
            errors["specialization"] = "Please select a specialization."
        if not data["hospital"]:
            errors["hospital"] = "Hospital name is required."
        if not data["country"]:
            errors["country"] = "Please select a country."
        if not data["city"]:
            errors["city"] = "Please enter or select a city."
        if not errors:
            request.session["dr_step2"] = data
            return redirect("physicians:physician_register_step3")
        return render(request, "physicians/register_step2.html", {
            "data": data, "errors": errors, "step": 2,
            "specializations": specializations, "countries": WORLD_COUNTRIES,
        })

    return render(request, "physicians/register_step2.html", {
        "data": request.session.get("dr_step2", {}),
        "errors": {},
        "step": 2,
        "specializations": specializations,
        "countries": WORLD_COUNTRIES,
    })


def physician_register_step3(request):
    """Step 3: Bio & notes — then save the request."""
    if "dr_step1" not in request.session or "dr_step2" not in request.session:
        return redirect("physicians:physician_register")

    if request.method == "POST":
        bio   = request.POST.get("bio", "").strip()
        notes = request.POST.get("notes", "").strip()

        step1 = request.session["dr_step1"]
        step2 = request.session["dr_step2"]

        # Create an inactive user account — activated when admin approves
        user = Mother.objects.create_user(
            phone_number = step1["phone"],
            password     = step1["password"],
            full_name    = step1["full_name"],
            email        = step1["email"] or None,
            city         = step2.get("city", ""),
            country      = step2.get("country", "Kenya"),
            is_active    = False,
            is_doctor    = True,
        )

        PhysicianRegistrationRequest.objects.create(
            full_name      = step1["full_name"],
            phone          = step1["phone"],
            email          = step1["email"],
            specialization = step2["specialization"],
            hospital       = step2["hospital"],
            country        = step2.get("country", ""),
            city           = step2["city"],
            license_number = step2["license_number"],
            bio            = bio,
            notes          = notes,
            user           = user,
        )

        # Clean up session
        del request.session["dr_step1"]
        del request.session["dr_step2"]

        return redirect("physicians:registration_success")

    return render(request, "physicians/register_step3.html", {
        "data": {"bio": "", "notes": ""},
        "errors": {},
        "step": 3,
    })


def registration_success(request):
    return render(request, "physicians/registration_success.html")


# ── AI recommendation endpoint ────────────────────────────────────────────────
@login_required
def recommend_doctors(request):
    """
    Returns top 3 recommended doctors as JSON.
    Called by the chat and cry analyser when a serious issue is detected.
    Query params: spec (specialization), lat, lon
    """
    spec = request.GET.get("spec", "pediatrician")
    lat  = request.GET.get("lat")
    lon  = request.GET.get("lon")

    doctors = Physician.objects.filter(
        status="approved",
        is_available=True,
        specialization=spec
    )

    doctor_list = list(doctors)

    if lat and lon:
        try:
            lat, lon = float(lat), float(lon)
            doctor_list.sort(key=lambda p: p.distance_from(lat, lon))
        except (ValueError, TypeError):
            pass

    top3 = doctor_list[:3]

    data = [{
        "id":             str(d.pk),
        "name":           f"Dr. {d.full_name}",
        "specialization": d.get_specialization_display(),
        "hospital":       d.hospital,
        "phone":          d.phone,
        "city":           d.city,
        "rating":         float(d.rating),
        "distance_km":    round(d.distance_from(float(lat), float(lon)), 1) if lat and lon else None,
    } for d in top3]

    return JsonResponse({"doctors": data})
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from formtools.wizard.views import SessionWizardView
from django.contrib import messages
from django.utils import timezone
from .models import Mother, Child
from .forms import (
    MotherStep1Form, MotherStep2Form, MotherStep3Form,
    ChildForm, LoginForm
)
from physicians.views import WORLD_COUNTRIES


# ─── Registration: Step 1 — Basic Info ───────────────────────────────────────

def register_step1(request):
    """Step 1: Full name + phone number + password"""
    if request.user.is_authenticated:
        return redirect("mothers:home")

    form = MotherStep1Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Store in session, don't save yet
        request.session["reg_step1"] = {
            "full_name": form.cleaned_data["full_name"],
            "phone_number": form.cleaned_data["phone_number"],
            "email": form.cleaned_data.get("email", ""),
            "password": form.cleaned_data["password1"],
        }
        return redirect("mothers:register_step2")

    return render(request, "mothers/register_step1.html", {"form": form, "step": 1})


def register_step2(request):
    """Step 2: Emergency contact"""
    if request.user.is_authenticated:
        return redirect("mothers:home")

    if "reg_step1" not in request.session:
        return redirect("mothers:register_step1")

    form = MotherStep2Form(request.POST or None)
    if request.method == "POST":
        if "skip" in request.POST:
            request.session["reg_step2"] = {}
            return redirect("mothers:register_step3")
        if form.is_valid():
            request.session["reg_step2"] = {
                "emergency_contact_name": form.cleaned_data.get("emergency_contact_name", ""),
                "emergency_contact_phone": form.cleaned_data.get("emergency_contact_phone", ""),
                "emergency_contact_relationship": form.cleaned_data.get("emergency_contact_relationship", ""),
            }
            return redirect("mothers:register_step3")

    return render(request, "mothers/register_step2.html", {"form": form, "step": 2})


def register_step3(request):
    """Step 3: Location — then create account"""
    if request.user.is_authenticated:
        return redirect("mothers:home")

    if "reg_step1" not in request.session:
        return redirect("mothers:register_step1")

    form = MotherStep3Form(request.POST or None)
    if request.method == "POST":
        if "skip" in request.POST or form.is_valid():
            step1 = request.session.get("reg_step1", {})
            step2 = request.session.get("reg_step2", {})

            city = ""
            country = "Kenya"
            if form.is_valid():
                city = form.cleaned_data.get("city", "")
                country = form.cleaned_data.get("country", "Kenya")

            try:
                mother = Mother.objects.create_user(
                    phone_number=step1["phone_number"],
                    password=step1["password"],
                    full_name=step1["full_name"],
                    email=step1.get("email", ""),
                    emergency_contact_name=step2.get("emergency_contact_name", ""),
                    emergency_contact_phone=step2.get("emergency_contact_phone", ""),
                    emergency_contact_relationship=step2.get("emergency_contact_relationship", ""),
                    city=city,
                    country=country,
                )
                # Clear session
                for key in ["reg_step1", "reg_step2"]:
                    request.session.pop(key, None)

                # Auto login
                login(request, mother)
                messages.success(request, f"Welcome to MamaCare, {mother.first_name}! 🌸")
                return redirect("mothers:add_child")

            except Exception as e:
                messages.error(request, f"Something went wrong: {str(e)}")

    return render(request, "mothers/register_step3.html", {"form": form, "step": 3, "countries": WORLD_COUNTRIES})


# ─── Login / Logout ───────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("mothers:home")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone_number"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=phone, password=password)
        if user:
            login(request, user)
            if user.is_doctor:
                return redirect("physicians:physician_home")
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("mothers:home")
        else:
            messages.error(request, "Incorrect phone number or password.")

    return render(request, "mothers/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("mothers:login")


# ─── Home ─────────────────────────────────────────────────────────────────────

@login_required
def home(request):
    mother = request.user
    children = mother.children.filter(is_active=True).order_by("date_of_birth")
    context = {
        "mother": mother,
        "children": children,
        "greeting": get_greeting(),
    }
    return render(request, "mothers/home.html", context)


# ─── Child Management ─────────────────────────────────────────────────────────

@login_required
def add_child(request):
    """
    Single-view, single-template multi-step child registration.
    All steps live in mothers/add_child.html; navigation is handled
    entirely in JavaScript — no SessionWizardView or extra templates needed.
    """
    form = ChildForm(request.POST or None, request.FILES or None)
 
    if request.method == "POST" and form.is_valid():
        child = form.save(commit=False)
        child.mother = request.user
        child.save()
        messages.success(request, f"🎉 {child.name} has been added to your profile!")
        return redirect("mothers:home")
 
    return render(request, "mothers/add_child.html", {"form": form})


@login_required
def child_detail(request, pk):
    child = get_object_or_404(Child, pk=pk, mother=request.user)
    return render(request, "mothers/child_detail.html", {"child": child})


@login_required
def edit_child(request, pk):
    child = get_object_or_404(Child, pk=pk, mother=request.user)
    form = ChildForm(request.POST or None, request.FILES or None, instance=child)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{child.name}'s info updated! 💕")
        return redirect("mothers:child_detail", pk=child.pk)
    return render(request, "mothers/add_child.html", {"form": form, "child": child, "editing": True})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile(request):
    mother = request.user
    return render(request, "mothers/profile.html", {"mother": mother})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_greeting():
    hour = timezone.localtime(timezone.now()).hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    return "Good evening"
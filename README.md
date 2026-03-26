# MamaCare

AI-powered maternal and infant care platform built for the Microsoft AI Challenge.

---

## What It Does

MamaCare connects new mothers with AI guidance and real doctors — from asking why a baby is crying to booking an instant consultation.

| Feature | Description |
|---------|-------------|
| **AI Chat** | Streaming GPT responses via Azure OpenAI. Child-aware context, markdown, real-time typing |
| **Cry Analyser** | Records or uploads baby cry → ML model classifies type (hungry, tired, pain, etc.) with confidence |
| **Doctor Consultation** | Mother selects nearby doctor → request sent → doctor accepts → live chat |
| **Web Push Notifications** | Doctor receives push alert on device when a consultation is requested |
| **PWA** | Installable on Android & iOS, offline support, service worker caching |
| **Doctor Portal** | Separate dashboard, inbox, consultation management, severity badges |

---

## Tech Stack

### Microsoft / Azure
| Resource | Purpose |
|----------|---------|
| **Azure App Service** (P0v3, Linux) | Hosts the Django application |
| **Azure Database for PostgreSQL** (Flexible Server v14) | Production database on private VNet |
| **Azure OpenAI** (GPT via AI Foundry) | Powers the AI chat assistant and symptom assessment |
| **GitHub Actions + OIDC** | CI/CD pipeline — deploys on every push to `main` |

### Application
| Technology | Purpose |
|------------|---------|
| **Django 6.0.3** | Web framework |
| **Python** | Backend language |
| **TensorFlow + scikit-learn** | Cry classification ML model |
| **pywebpush** | Web Push notifications (VAPID) |
| **WhiteNoise** | Static file serving in production |
| **Gunicorn** | WSGI server |
| **SQLite** (dev) / **PostgreSQL** (prod) | Database |

---

## Project Structure

```
mamacare/
├── mothers/          # Mother accounts, registration, home, profile
├── physicians/       # Doctor profiles, registration, directory
├── chat/             # AI chat with Azure OpenAI streaming
├── predictions/      # Cry analyser (ML model + results)
├── consultations/    # Consultation request → accept → live chat
├── notifications/    # Web Push subscriptions + sending
├── reminders/        # (Planned) Azure Functions push reminders
├── core/             # Settings, URLs, context processors
└── static/           # PWA manifest, service worker, icons
```

---

## Environment Variables

### Local (`.env`)
```
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=                        # leave blank for SQLite

AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT=

VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY_B64=               # base64-encoded PEM
VAPID_ADMIN_EMAIL=
```

### Production (Azure App Settings)
Same keys as above plus:
```
DATABASE_URL=postgres://...
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.azurewebsites.net
```

---

## Local Development

```bash
# 1. Clone and create venv
git clone https://github.com/enricoshilisia/mamacareai.git
cd mamacare
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and fill in env vars
cp .env.example .env

# 4. Migrate and run
python manage.py migrate
python manage.py runserver
```

---

## Deployment

Push to `main` — GitHub Actions builds and deploys to Azure App Service automatically via OIDC (no stored credentials).

**Azure startup command:**
```
python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
```

---

## How the Consultation Flow Works

```
Mother asks AI about symptoms
    → taps "Get Doctor Advice"
    → AI assesses severity from chat history
    → nearby doctors shown (sorted by GPS distance)
    → mother selects doctor → request created
    → Doctor receives Web Push notification
    → Doctor accepts → live consultation chat opens
    → Doctor marks complete
```

---

## Microsoft Challenge

Built for the **Microsoft AI Challenge** using:
- Azure OpenAI (AI Foundry) for all AI features
- Azure App Service for hosting
- Azure PostgreSQL for data
- GitHub Actions with Microsoft OIDC for deployment

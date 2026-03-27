from pathlib import Path
import dj_database_url
from decouple import config as env, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ─────────────────────────────────────────────────────────────────

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")

DEBUG = env("DJANGO_DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = env(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = env(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
    cast=Csv(),
)

# ─── Apps ─────────────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # MamaCare apps
    'mothers',
    'reminders',
    'chat',
    'predictions',
    'physicians',
    'consultations',
    'notifications',
    'prescriptions',
]

# ─── Auth ─────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = 'mothers.Mother'
LOGIN_URL = 'mothers:login'
LOGIN_REDIRECT_URL = 'mothers:home'
LOGOUT_REDIRECT_URL = 'mothers:login'

# ─── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'core.middleware.AzureHealthProbeMiddleware',  # must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serve static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# ─── Templates ────────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.vapid_public_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ─── Database ─────────────────────────────────────────────────────────────────
# In development: uses SQLite (no DATABASE_URL set).
# In production:  set DATABASE_URL in Azure App Settings, e.g.:
#   postgres://USER:PASSWORD@HOST:5432/DBNAME

_db_url = env("DATABASE_URL", default=None)

if _db_url:
    DATABASES = {
        "default": dj_database_url.parse(_db_url, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Password validation ──────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalisation ─────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# ─── Static & Media ───────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise compression for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Default primary key ──────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Azure OpenAI ─────────────────────────────────────────────────────────────

AZURE_OPENAI_ENDPOINT    = env("AZURE_OPENAI_ENDPOINT", default="")
AZURE_OPENAI_KEY         = env("AZURE_OPENAI_KEY", default="")
AZURE_OPENAI_DEPLOYMENT  = env("AZURE_OPENAI_DEPLOYMENT", default="")
AZURE_OPENAI_API_VERSION = env("AZURE_OPENAI_API_VERSION", default="2024-05-01-preview")

# ─── Web Push (VAPID) ─────────────────────────────────────────────────────────
# VAPID_PUBLIC_KEY  → URL-safe base64 uncompressed EC point (sent to browser)
# VAPID_PRIVATE_KEY_B64 → base64-encoded PEM (stored in env, decoded below)
# Add both to Azure App Settings and local .env

import base64 as _b64

# Fallback VAPID keys (used when env vars are missing or corrupt)
_FALLBACK_VAPID_PUBLIC  = "BOs8yNAsL6OKjqQyzP42Jai4uo1siOTf6RxFApraaCZ8rjz8babtFgU1H9OQhvjKgkN2bbr2uhwjmpbRyfdDw4o"
_FALLBACK_VAPID_PRIVATE = "LS0tLS1CRUdJTiBFQyBQUklWQVRFIEtFWS0tLS0tCk1IY0NBUUVFSUhSay9kaERKZ3BJN2REdmhyN3ZlOGcvODBXNExVQ3lqeXlRTk9QS2ZkSlRvQW9HQ0NxR1NNNDkKQXdFSG9VUURRZ0FFNnp6STBDd3ZvNHFPcERMTS9qWWxxTGk2ald5STVOL3BIRVVDbXRwb0pueXVQUHh0cHUwVwpCVFVmMDVDRytNcUNRM1p0dXZhNkhDT2FsdEhKOTBQRGlnPT0KLS0tLS1FTkQgRUMgUFJJVkFURSBLRVktLS0tLQo"

VAPID_PUBLIC_KEY  = env("VAPID_PUBLIC_KEY", default=_FALLBACK_VAPID_PUBLIC)

# VAPID_PRIVATE_KEY_RAW — raw base64url EC key (preferred, no PEM parsing)
# VAPID_PRIVATE_KEY     — raw PEM string (legacy)
# VAPID_PRIVATE_KEY_B64 — base64-encoded PEM (legacy)
_raw_key  = env("VAPID_PRIVATE_KEY_RAW", default="")
_raw_pem  = env("VAPID_PRIVATE_KEY", default="")
_priv_b64 = env("VAPID_PRIVATE_KEY_B64", default="")
if _raw_key:
    VAPID_PRIVATE_KEY = _raw_key  # pass directly to pywebpush — no PEM needed
elif _raw_pem:
    VAPID_PRIVATE_KEY = _raw_pem.replace("\\n", "\n").strip()
elif _priv_b64:
    try:
        VAPID_PRIVATE_KEY = _b64.urlsafe_b64decode(_priv_b64 + "==").decode().strip()
    except Exception:
        VAPID_PRIVATE_KEY = _b64.urlsafe_b64decode(_FALLBACK_VAPID_PRIVATE + "==").decode().strip()
else:
    VAPID_PRIVATE_KEY = _b64.urlsafe_b64decode(_FALLBACK_VAPID_PRIVATE + "==").decode().strip()

VAPID_ADMIN_EMAIL = env("VAPID_ADMIN_EMAIL", default="admin@mamacare.com")

# ─── Production security hardening ────────────────────────────────────────────

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    X_FRAME_OPTIONS = 'DENY'

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
]

# ─── Auth ─────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = 'mothers.Mother'
LOGIN_URL = 'mothers:login'
LOGIN_REDIRECT_URL = 'mothers:home'
LOGOUT_REDIRECT_URL = 'mothers:login'

# ─── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
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

# ─── Production security hardening ────────────────────────────────────────────

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    X_FRAME_OPTIONS = 'DENY'

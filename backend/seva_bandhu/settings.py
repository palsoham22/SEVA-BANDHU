"""Django settings for the Seva Bandhu project."""
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set. Copy .env.example to .env and provide a value.")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [item.strip() for item in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,seva-bandhu.onrender.com").split(",") if item.strip()]
CSRF_TRUSTED_ORIGINS = [item.strip() for item in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "https://seva-bandhu.onrender.com").split(",") if item.strip()]
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
INSTALLED_APPS = ["daphne", "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "channels", "core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "seva_bandhu.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR.parent / "SevaBandhu-Frontend" / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.template.context_processors.csrf", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages", "core.context_processors.firebase_config"]}}]
WSGI_APPLICATION = "seva_bandhu.wsgi.application"
ASGI_APPLICATION = "seva_bandhu.asgi.application"
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
DATABASES = {"default": dj_database_url.config(default=os.environ["DATABASE_URL"])} if os.environ.get("DATABASE_URL") else {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND") or (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG and not EMAIL_HOST
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() in {"1", "true", "yes", "on"}
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() in {"1", "true", "yes", "on"}
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "15"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost")

FIREBASE_CONFIG = {
    "api_key": os.environ.get("FIREBASE_API_KEY", ""),
    "auth_domain": os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
    "project_id": os.environ.get("FIREBASE_PROJECT_ID", ""),
    "storage_bucket": os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
    "messaging_sender_id": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
    "app_id": os.environ.get("FIREBASE_APP_ID", ""),
}

# --- SMART OFFER CONFIGURATION ---
SMART_OFFER_VIEW_THRESHOLD = 3
SMART_OFFER_WINDOW_HOURS = 24
SMART_OFFER_COOLDOWN_HOURS = 24


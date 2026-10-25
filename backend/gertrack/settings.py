import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Sécurité ────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ─── Applications ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'daphne',    # doit être en tête : remplace runserver par un serveur ASGI
    'channels',  # doit précéder staticfiles pour que runserver serve en ASGI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    # Apps GerTrack
    'apps.accounts',
    'apps.products',
    'apps.suppliers',
    'apps.stock',
    'apps.operations',
    'apps.requests',
    'apps.notifications', 
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',   # doit être EN PREMIER
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.accounts.middleware.CurrentRequestMiddleware',
]

ROOT_URLCONF = 'gertrack.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'gertrack.wsgi.application'
ASGI_APPLICATION = 'gertrack.asgi.application'

# ─── Centre de notifications temps réel (Phase G — §9) ────────────────────────
# Couche mémoire : suffisante pour un seul worker (manage.py runserver / un
# process de prod simple). Passer à channels_redis si un déploiement
# multi-worker est nécessaire un jour.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# ─── Base de données PostgreSQL ───────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     os.getenv('DB_NAME',     'gertrack_db'),
        'USER':     os.getenv('DB_USER',     'gertrack_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'gertrack_pass'),
        'HOST':     os.getenv('DB_HOST',     'localhost'),
        'PORT':     os.getenv('DB_PORT',     '5432'),
    }
}

# ─── Authentification ─────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# ─── DRF + JWT ────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'AUTH_HEADER_TYPES':      ('Bearer',),
    # Sans ceci, User.last_login n'est jamais mis à jour : SimpleJWT ne passe
    # pas par django.contrib.auth.login() (pas de session), donc le signal
    # user_logged_in n'est envoyé que si ce réglage l'active explicitement.
    'UPDATE_LAST_LOGIN':      True,
}

# ─── CORS (autorise React sur port 3000) ──────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# ─── Fichiers ─────────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Localisation ─────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE     = 'Africa/Dakar'
USE_I18N      = True
USE_TZ        = True

# ─── Infos entreprise ─────────────────────────────────────────────────────────
COMPANY_NAME    = os.getenv('COMPANY_NAME',    'GERTECH ')
COMPANY_ADDRESS = os.getenv('COMPANY_ADDRESS', 'Dakar, Sénégal')
COMPANY_PHONE   = os.getenv('COMPANY_PHONE',   '+221 33 832 84 30')
COMPANY_EMAIL   = os.getenv('COMPANY_EMAIL',   'contact@gertech-e-services.com')

# Modèle user personnalisé
AUTH_USER_MODEL = 'accounts.User'
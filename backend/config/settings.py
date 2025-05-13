# settings.py
from pathlib import Path
import os
import dj_database_url # Assurez-vous que cet import ne cause plus d'erreur

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Clé Secrète ---
# Lue depuis une variable d'environnement en production (DJANGO_SECRET_KEY)
# Gardez votre clé actuelle comme fallback pour le développement local si DJANGO_SECRET_KEY n'est pas définie.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-kxzwc71wc#4-8(n!bv9m06jzh#g9isaj@*w%jbz$6v7cxhid$a')

# --- Mode Debug ---
# Doit être False en production. Lu depuis une variable d'environnement.
# Par défaut à 'False'. Vous pouvez créer une variable DJANGO_DEBUG='True' sur Render
# uniquement pour du débogage temporaire (non recommandé pour une longue durée).
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True' # MODIFIÉ

# --- Hôtes Autorisés ---
# Sera configuré avec l'URL de votre application Render.
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
# Vous pouvez ajouter '.onrender.com' pour couvrir les builds initiaux si la var d'env n'est pas dispo,
# ou ajouter manuellement votre URL Render (ex: 'mon-app.onrender.com') après le premier déploiement.
# ALLOWED_HOSTS.append('mon-app-mk.onrender.com') # Exemple

# --- Applications Installées ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # AJOUTÉ: Pour servir les statiques avec WhiteNoise en DÉVELOPPEMENT si DEBUG=False
    'django.contrib.staticfiles',
    'rest_framework.authtoken',
    'rest_framework',
    'corsheaders',
    'api', # Votre application
]

# --- Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # AJOUTÉ: Placé haut, juste après SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',      # MODIFIÉ: Bon placement (avant CommonMiddleware)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls' # Assurez-vous que 'config' est bien le nom du dossier de votre projet principal

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', # Souvent utile
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application' # Assurez-vous que 'config' est bien le nom du dossier de votre projet

# --- Configuration de la Base de Données ---
# Utilise DATABASE_URL de l'environnement (fourni par Render pour PostgreSQL)
# et fallback sur SQLite pour le développement local si DATABASE_URL n'est pas définie.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600, # Recommandé par Render
        # Render s'attend à ce que ssl_require soit True pour ses bases de données managées.
        # dj_database_url devrait le gérer si l'URL de la BDD contient sslmode=require.
        # Sinon, on peut le forcer si on est sur Render.
        ssl_require=True if 'RENDER' in os.environ else False
    )
}
# Si vous rencontrez des problèmes SSL avec Render et dj_database_url,
# vous pouvez explicitement ajouter les options SSL si DATABASE_URL vient de Render :
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql' and 'RENDER' in os.environ:
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}


# --- Validation des Mots de Passe ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# --- Internationalisation ---
LANGUAGE_CODE = 'fr-fr' # MODIFIÉ: Français
TIME_ZONE = 'Europe/Paris'  # MODIFIÉ: Fuseau horaire de Paris

USE_I18N = True
USE_TZ = True

# --- Fichiers Statiques (CSS, JavaScript, Images) ---
STATIC_URL = '/static/'
# Dossier où `collectstatic` rassemblera tous les fichiers statiques pour le déploiement
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # AJOUTÉ
# Pour que WhiteNoise puisse servir les fichiers statiques en production de manière optimisée
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' # AJOUTÉ

# --- Type de Clé Primaire par Défaut ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Configuration CORS ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Vous ajouterez ici l'URL de votre frontend déployé (ex: "https://votre-app.netlify.app")
]
# Si vous utilisez des cookies ou des sessions avec des requêtes cross-origin (pas le cas avec TokenAuth simple)
# CORS_ALLOW_CREDENTIALS = True
# Pour tester au début si vous avez des soucis CORS (moins sécurisé, à restreindre ensuite):
# CORS_ALLOW_ALL_ORIGINS = True

# --- Configuration Django REST Framework (Recommandé) ---
REST_FRAMEWORK = { # AJOUTÉ
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        # 'rest_framework.authentication.SessionAuthentication', # Si vous utilisez aussi l'API navigable pour le dev
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly', # Ou une permission plus restrictive par défaut
    ]
}
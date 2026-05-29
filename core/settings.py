
from datetime import timedelta

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-$-z^^ziw7ye2ltvz$@_gp*+l62rt3g(x!2$49j3str&5=36w9u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    'rest_framework_simplejwt',
    "django_filters",
    "corsheaders",
]
LOCAL_APPS = [
    'apps.organizacao',
    'apps.utilizadores',
    "apps.faturacao",
    "common",
    'apps.clientes',
    "apps.dashboard",
    # Aqui você pode adicionar apps locais específicos do seu projeto
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

# 2. Configurar o REST Framework para usar JWT por padrão
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
     'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',
        'apps.utilizadores.authentication.SingleTokenAuthentication', # A tua nova classe
        'rest_framework.authentication.SessionAuthentication', # ADICIONA ESTA LINHA

    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

   


# 3. Definições do Token (Seguindo o documento de engenharia)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'JTI_CLAIM': 'jti', # Certifica-te que esta linha existe ou é o padrão
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id', # Como usamos UUID
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': 'apps.utilizadores.serializers.MyTokenObtainPairSerializer',
}



MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Deve estar no TOPO da lista
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.43.5:3000", # Teu IP de rede que vimos no log anterior
]

# Se quiseres permitir tudo apenas durante o desenvolvimento (não recomendado em produção)
# CORS_ALLOW_ALL_ORIGINS = True 

# Importante para o que definimos nos Cookies
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'apps/faturacao/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'


import os

# Caminho onde as imagens serão guardadas no disco
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# No final do settings.py
AUTH_USER_MODEL = 'utilizadores.CustomUser'

AUTHENTICATION_BACKENDS = [
    'apps.utilizadores.backends.EmailOrUsernameModelBackend', # Ex: 'apps.utilizadores.backends...'
    'django.contrib.auth.backends.ModelBackend', # Mantém o padrão como reserva
]


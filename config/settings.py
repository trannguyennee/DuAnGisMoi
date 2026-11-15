import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Secrets & môi trường ----------------------------------------------------
# Mọi giá trị nhạy cảm được đọc từ biến môi trường (hoặc file .env khi chạy local).
# Xem .env.example. TUYỆT ĐỐI không commit SECRET_KEY thật vào git.
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# Mặc định TẮT debug. Chỉ bật khi dev local bằng DJANGO_DEBUG=True trong .env
DEBUG = env_bool('DJANGO_DEBUG', False)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-dev-only'  # chỉ dùng khi DEBUG  # gitleaks:allow  # nosec B105
    else:
        raise ImproperlyConfigured(
            'Thiếu biến môi trường DJANGO_SECRET_KEY. Tạo key mới bằng: '
            'python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

# Railway tự cấp tên miền public qua biến RAILWAY_PUBLIC_DOMAIN -> không cần dùng '*'
RAILWAY_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_DOMAIN}')

# --- Bảo mật khi chạy production (DEBUG=False) --------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Railway đứng sau proxy HTTPS
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '2592000'))  # 30 ngày
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

# Giới hạn upload: ảnh hiện trường tối đa 5 MB (kiểm tra trong views)
MAX_UPLOAD_IMAGE_BYTES = 5 * 1024 * 1024
# Phục vụ file media (ảnh upload) qua Django. Tắt nếu chuyển sang S3/CDN.
SERVE_MEDIA = env_bool('DJANGO_SERVE_MEDIA', True)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'maps',
    'django.contrib.gis', # App GIS quan trọng
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise phục vụ file static khi chạy bằng gunicorn (DEBUG=False)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Tự động kết nối với Postgres của Railway thông qua biến DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        engine='django.contrib.gis.db.backends.postgis',
        conn_max_age=600,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# Static & Media files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Cho phép WhiteNoise đọc thẳng static trong app, không bắt buộc chạy collectstatic
WHITENOISE_USE_FINDERS = True

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
LOGIN_URL = 'login'

# --- CẤU HÌNH GIS (GDAL/GEOS) ---

# Ưu tiên biến môi trường; nếu không có thì dùng đường dẫn mặc định trên Windows.
if os.name == 'nt':
    _pg_bin = os.environ.get('POSTGRES_BIN', r'C:\Program Files\PostgreSQL\16\bin')
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH', os.path.join(_pg_bin, 'libgdal-35.dll'))
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH', os.path.join(_pg_bin, 'libgeos_c.dll'))
else:
    # Linux (Railway/CI): lấy từ ENV, nếu trống Django tự tìm thư viện hệ thống
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH')
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH')

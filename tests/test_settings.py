import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'akfjnakfcjaldunfkhaldfhalshf'
INSTALLED_APPS = [
    'django.contrib.auth',
    "django.contrib.contenttypes",
    "adminsortable2",
    'easy_thumbnails',
    'filer',
    'mptt',
    'imagedeck',
    'polymorphic',    
    "dcodex",
    "dcodex_bible",
    "dcodex_lectionary",
    "tests",
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

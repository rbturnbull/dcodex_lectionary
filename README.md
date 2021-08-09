# dcodex_lectionary
`Extension for D-Codex to use lectionaries`

## Installation

For a brand new DCodex site, it is easiest to install using [dcodex-cookiecutter](https://github.com/rbturnbull/dcodex-cookiecutter).

To install dcodex-lectionary as a plugin in a dcodex site already set up. Install with pip:
```
pip install -e https://github.com/rbturnbull/dcodex_lectionary.git#egg=dcodex_lectionary
```

Then add to your installed apps (after dcodex_bible):
```
INSTALLED_APPS += [
    "dcodex_bible",
    "dcodex_lectionary",
]
```

Then add the urls to your main urls.py:
```
urlpatterns += [
    path('dcodex_lectionary/', include('dcodex_lectionary.urls')),    
]
```

## Database Fixture

To use the standard versification system of the Old and New Testaments, install the database fixtures:

```
python manage.py loaddata lectionarydays
```
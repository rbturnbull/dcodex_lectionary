from django.urls import path

from . import views

urlpatterns = [
    path('ajax/lection-verses/', views.lection_verses, name='dcodex-lectionary-lection-verses'),
]


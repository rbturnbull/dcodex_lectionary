from django.urls import path

from . import views

urlpatterns = [
    path('ajax/lection-verses/', views.lection_verses, name='dcodex-lectionary-lection-verses'),
    path('ms/<str:request_siglum>/count/', views.count, name='dcodex-lectionary-count'),    
    path('ms/<str:request_siglum>/<str:comparison_sigla_string>/similarity/', views.similarity, name='dcodex-lectionary-similarity'),    
    path('ms/<str:request_siglum>/<str:comparison_sigla_string>/similarity_probabilities/', views.similarity_probabilities, name='dcodex-lectionary-similarity_probabilities'),    
    path('ms/<str:request_sigla>/<str:request_lections>/complete/', views.complete, name='dcodex-lectionary-complete'),    
]


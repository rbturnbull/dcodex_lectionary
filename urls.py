from django.urls import path

from . import views

urlpatterns = [
    path('ajax/lection-verses/', views.lection_verses, name='dcodex-lectionary-lection-verses'),
    path('ajax/add-lection-box/', views.add_lection_box, name='dcodex-lectionary-add-lection-box'),
    path('ajax/insert-lection/', views.insert_lection, name='dcodex-lectionary-insert-lection'),
    path('ajax/create-lection/', views.create_lection, name='dcodex-lectionary-create-lection'),
    path('ajax/insert-reference/', views.insert_reference, name='dcodex-lectionary-insert-reference'),
    
    path('ajax/lection-suggestions/', views.lection_suggestions, name='dcodex-lectionary-lection-suggestions'),    
    
    path('ms/<str:request_siglum>/count/', views.count, name='dcodex-lectionary-count'),    
    path('ms/<str:request_siglum>/<str:comparison_sigla_string>/similarity/', views.similarity, name='dcodex-lectionary-similarity'),    
    path('ms/<str:request_siglum>/<str:comparison_sigla_string>/similarity_probabilities/', views.similarity_probabilities, name='dcodex-lectionary-similarity_probabilities'),    
    path('ms/<str:request_sigla>/<str:request_lections>/complete/', views.complete, name='dcodex-lectionary-complete'),    
]


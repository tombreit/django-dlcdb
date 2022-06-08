from django.urls import path
from .views import (
    person_search,
    person_detail,
    add_assignement,
    remove_assignement,
    get_assignements,
)


app_name = 'smallstuff'

urlpatterns = [
    path('search/', person_search, name="person_search"),
    path('person/<int:person_id>', person_detail, name='person_detail'),
    
    path('assignements/person/<int:person_id>/add', add_assignement, name='add_assignement'),
    path('assignements/person/<int:person_id>/<str:state>', get_assignements, name='get_assignements'),
    path('assignements/remove/<int:assignment_id>', remove_assignement, name='remove_assignement'),
]

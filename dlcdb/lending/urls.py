from django.urls import path
from .views import (
    person_search,
    person_detail,
    add_lending,
)


app_name = 'lending'

urlpatterns = [
    path('person/search/', person_search, name="person_search"),
    path('person/<int:person_id>', person_detail, name='person_detail'),
    path('person/<int:person_id>/add_lending', add_lending, name='add_lending'),
]

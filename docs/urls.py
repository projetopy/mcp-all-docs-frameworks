from django.urls import path
from .views import search_docs

urlpatterns = [
    path("search/", search_docs, name="search_docs"),
]

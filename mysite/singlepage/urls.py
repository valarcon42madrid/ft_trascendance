from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name='index'),
    path('sections/home', views.home_section, name='home_section'),
]
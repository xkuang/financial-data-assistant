from django.urls import path
from . import views

app_name = 'docs'

urlpatterns = [
    path('', views.documentation, name='documentation'),
] 
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_interface, name='chat_interface'),
    path('query/', views.process_query, name='process_query'),
    path('analyze/', views.analyze_trends, name='analyze_trends'),
    path('sql/', views.sql_query, name='sql_query'),
] 
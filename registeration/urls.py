from django.urls import path
from django.conf.urls import url
from . import views


app_name = 'registeration'

urlpatterns = [
    path('register/', views.register_view, name="register"),
    path('verify/', views.verify_view, name="verify"),
    path('error/', views.error, name="error"),
    path('', views.home_view, name="home")
]

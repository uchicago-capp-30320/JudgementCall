from django.urls import path
from . import views

app_name = "judgement_call"

urlpatterns = [
    path("judges/<str:zip_code>/", views.zip_judge, name="zip_judge")
]
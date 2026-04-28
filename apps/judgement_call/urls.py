from django.urls import path
from . import views

app_name = "judgement_call"

urlpatterns = [
    path("judges_state_county/<str:state>/<str:county>/", views.judges_state_county, name="judges_state_county"),
    path("people/<int:person_id>/", views.show_person, name="show_person")
]
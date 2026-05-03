from django.urls import path
from . import views as views

app_name = "judgement_call"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("judges/", views.judges, name="judges"),
    path(
        "judges/<str:state>/<str:county>/",
        views.judges_state_county,
        name="judges_state_county",
    ),
    path("people/<int:person_id>/", views.show_person, name="show_person"),
    path("about/", views.about, name="about"),
    path("elections/", views.elections, name="elections"),
    path("candidates/<str:state>/<str:county>/", views.candidates, name="candidates"),
    path("analysis/", views.analysis, name="analysis"),
    path("api/counties/<str:state>/", views.get_counties, name="get_counties"),
]

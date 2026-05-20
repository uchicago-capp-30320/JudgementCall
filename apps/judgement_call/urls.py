from django.urls import path
from . import views

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
    path(
        "elections/<str:state>/<str:county>/",
        views.elections_state_county,
        name="elections_state_county",
    ),
    path("candidates/<str:state>/<str:county>/", views.candidates, name="candidates"),
    path("analysis/", views.analysis, name="analysis"),
    path("api/counties/<str:state>/", views.get_counties, name="get_counties"),
    path("gantt/", views.gantt, name="gantt"),
    path("judges/<str:court_id>", views.court_full_view, name="court"),
]

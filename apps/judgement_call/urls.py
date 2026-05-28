from django.urls import path, register_converter
from urllib.parse import unquote
from . import views

app_name = "judgement_call"


class StrListConverter:
    regex = r"[a-zA-ZÑñ0-9_\-\s%\.]+"  # Susan M. Crawford gets lost because of her Period!!!

    def to_python(self, value):
        if not value:
            return []

        value_decoded = unquote(value)
        return value_decoded.split("__")

    def to_url(self, value):
        return "__".join(value)


register_converter(StrListConverter, "str2list")

urlpatterns = [
    path("", views.landing, name="landing"),
    path("judges/", views.judges, name="judges"),
    path(
        "judges/<str:state>/<str:county>/",
        views.judges_state_county,
        name="judges_state_county",
    ),
    path("people/<int:person_id>/", views.show_person, name="show_person"),
    path("methodology/", views.methodology, name="methodology"),
    path("about/", views.about, name="about"),
    path("elections/", views.elections, name="elections"),
    path(
        "elections/<str:state>/<str:county>/",
        views.elections_state_county,
        name="elections_state_county",
    ),
    path("candidates/<str:state>/<str:county>/", views.candidates, name="candidates"),
    path("analysis/", views.analysis, name="analysis"),
    path("analysis/polarization/", views.polarization, name="polarization"),
    path("analysis/spacejam/", views.spacejam, name="spacejam"),
    path("api/counties/<str:state>/", views.get_counties, name="get_counties"),
    path("gantt/", views.gantt, name="gantt"),
    path(
        "radar/<str:court_id>/<str2list:persons>/",
        views.get_individual_opinions_for_radar,
        name="radar",
    ),
    path("spacejam/", views.spacejam_backup, name="spacejam_backup"),
    path("judges/<str:court_id>/", views.court_full_view, name="court"),
    path("clear-location/", views.clear_location, name="clear_location"),
]

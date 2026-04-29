from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls
from apps.judgement_call import views as judge_views

urlpatterns = [
    path("djadmin/", admin.site.urls),
    path("", judge_views.landing),
    path("about/", judge_views.about),
    path("elections/", judge_views.elections),
    path("candidates/<str:state>/<str:county>/", judge_views.candidates),
    # should we change analysis to analytics?
    path("analysis/", judge_views.analysis),
    path("judgement_call/", include("apps.judgement_call.urls")),
]

if settings.DEBUG and not settings.IS_TESTING:
    urlpatterns += debug_toolbar_urls()

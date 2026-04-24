from django.conf import settings
from django.contrib import admin
from django.urls import path, include
# from apps.judgement_call import views as judge_views

urlpatterns = [
    path("djadmin/", admin.site.urls),
    # path("", judge_views.index),
]

if settings.DEBUG and not settings.IS_TESTING:
    urlpatterns += debug_toolbar_urls()

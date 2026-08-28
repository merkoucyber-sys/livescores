from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from matches.views import control_login, control_logout, home, match_control, match_detail, team_detail, live_data

urlpatterns = [
    path("", home, name="home"),
    path("match/<int:pk>/", match_detail, name="match_detail"),
    path("team/<int:pk>/", team_detail, name="team_detail"),
    path("api/live/", live_data, name="live_data"),
    path("control/", match_control, name="match_control"),
    path("control/login/", control_login, name="control_login"),
    path("control/logout/", control_logout, name="control_logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

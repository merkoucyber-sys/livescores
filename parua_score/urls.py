from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from matches.views import home, match_detail, team_detail, live_data

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("match/<int:pk>/", match_detail, name="match_detail"),
    path("team/<int:pk>/", team_detail, name="team_detail"),
    path("api/live/", live_data, name="live_data"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

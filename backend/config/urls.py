from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

def health_check(request):
    if request.method == "HEAD":
        return HttpResponse(status=200)
    return HttpResponse("OK", status=200)

urlpatterns = [
    path("", health_check, name="health_check"),
    path("admin/", admin.site.urls),

    path(
        "api/",
        include("attendance.urls")
    ),

    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
]
from django.urls import path

from .views import (
    RegisterView,
    ProfileView,
    AttendanceView,
    DashboardView,
    LeaderboardView,
    ChallengesView,
    BadgesView,
    SyncAttendanceView,
)


urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("attendance/", AttendanceView.as_view()),
    path("dashboard/", DashboardView.as_view()),
    path("leaderboard/", LeaderboardView.as_view()),
    path("challenges/", ChallengesView.as_view()),
    path("badges/", BadgesView.as_view()),
    path("sync/", SyncAttendanceView.as_view()),
]
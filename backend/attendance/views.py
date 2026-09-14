from django.contrib.auth.models import User

from attendance.services.mongodb_service import get_cached_attendance

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

import traceback

from .models import Profile, Challenge, UserChallenge, Badge, UserBadge
from .serializers import ProfileSerializer, RegisterSerializer, LeaderboardSerializer


# ==========================================================
# REGISTER
# ==========================================================

class RegisterView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = RegisterSerializer(
            data=request.data
        )

        if serializer.is_valid():

            user = serializer.save()

            return Response(
                {
                    "message": "Account created successfully",
                    "roll_number": user.username,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ==========================================================
# PROFILE
# ==========================================================

class ProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        profile = Profile.objects.get(
            user=request.user
        )

        serializer = ProfileSerializer(profile)

        return Response(serializer.data)

    def patch(self, request):

        profile = Profile.objects.get(
            user=request.user
        )

        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


# ==========================================================
# ATTENDANCE
# ==========================================================

class AttendanceView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:

            profile = Profile.objects.get(
                user=request.user
            )

            # The Django username is the roll number
            roll_number = request.user.username

            # Get this user's attendance
            data = get_cached_attendance(
                roll_number
            )

            if not data:

                return Response(
                    {
                        "message": "No attendance data found.",
                        "attendance": []
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "roll_number": roll_number,
                    "attendance": data.get(
                        "attendance",
                        []
                    ),
                    "updated_at": data.get(
                        "updated_at"
                    ),
                },
                status=status.HTTP_200_OK,
            )

        except Profile.DoesNotExist:

            return Response(
                {
                    "message": "Profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:

            return Response(
                {
                    "message": "Failed to get attendance.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# ATTENDANCE STATUS
# ==========================================================

def get_attendance_status(percentage):

    if percentage >= 75:
        return "Safe"

    elif percentage >= 65:
        return "Warning"

    else:
        return "Critical"


# ==========================================================
# CLASSES NEEDED FOR 75%
# ==========================================================

def classes_needed_for_75(attended, total):

    if total == 0:
        return 0

    if (attended / total) * 100 >= 75:
        return 0

    classes = 0

    while (
        (attended + classes)
        / (total + classes)
    ) * 100 < 75:

        classes += 1

    return classes


# ==========================================================
# CLASSES THAT CAN BE MISSED
# ==========================================================

def classes_can_miss(attended, total):

    if total == 0:
        return 0

    if (attended / total) * 100 < 75:
        return 0

    classes = 0

    while (
        total + classes + 1 > 0
        and
        (
            attended
            / (total + classes + 1)
        ) * 100 >= 75
    ):

        classes += 1

    return classes


# ==========================================================
# DASHBOARD
# ==========================================================

class DashboardView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:

            # --------------------------------------------------
            # GET USER PROFILE
            # --------------------------------------------------

            profile = Profile.objects.get(
                user=request.user
            )

            # --------------------------------------------------
            # ROLL NUMBER
            # --------------------------------------------------

            # Django username = user's roll number
            roll_number = request.user.username

            # --------------------------------------------------
            # GET ATTENDANCE FROM MONGODB
            # --------------------------------------------------

            data = get_cached_attendance(
                roll_number
            )

            if not data:

                return Response(
                    {
                        "message": "No attendance data found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # --------------------------------------------------
            # RAW ATTENDANCE
            # --------------------------------------------------

            raw_attendance = data.get(
                "attendance",
                []
            )

            attendance = []

            total_attended = 0
            total_classes = 0

            # --------------------------------------------------
            # PROCESS EACH SUBJECT
            # --------------------------------------------------

            for item in raw_attendance:

                attended = int(
                    item.get(
                        "attended",
                        0
                    )
                )

                total = int(
                    item.get(
                        "total",
                        0
                    )
                )

                # ----------------------------------------------
                # PERCENTAGE
                # ----------------------------------------------

                if total > 0:

                    percentage = round(
                        (attended / total) * 100,
                        2
                    )

                else:

                    percentage = 0

                # ----------------------------------------------
                # STATUS
                # ----------------------------------------------

                subject_status = (
                    get_attendance_status(
                        percentage
                    )
                )

                # ----------------------------------------------
                # CLASSES NEEDED
                # ----------------------------------------------

                needed = (
                    classes_needed_for_75(
                        attended,
                        total
                    )
                )

                # ----------------------------------------------
                # CLASSES CAN MISS
                # ----------------------------------------------

                can_miss = (
                    classes_can_miss(
                        attended,
                        total
                    )
                )

                # ----------------------------------------------
                # ADD SUBJECT
                # ----------------------------------------------

                attendance.append(
                    {
                        "sno": item.get(
                            "sno"
                        ),

                        "subject": item.get(
                            "subject"
                        ),

                        "attended": attended,

                        "total": total,

                        "percentage": percentage,

                        "status": subject_status,

                        "classes_needed_for_75":
                            needed,

                        "classes_can_miss":
                            can_miss,
                    }
                )

                # ----------------------------------------------
                # OVERALL TOTALS
                # ----------------------------------------------

                total_attended += attended

                total_classes += total

            # ==================================================
            # OVERALL ATTENDANCE
            # ==================================================

            if total_classes > 0:

                overall_percentage = round(
                    (
                        total_attended
                        / total_classes
                    ) * 100,
                    2
                )

            else:

                overall_percentage = 0

            overall_status = (
                get_attendance_status(
                    overall_percentage
                )
            )

            # ==================================================
            # RESPONSE
            # ==================================================

            return Response(
                {
                    "username":
                        request.user.username,

                    "roll_number":
                        roll_number,

                    "overall": {

                        "attended":
                            total_attended,

                        "total":
                            total_classes,

                        "percentage":
                            overall_percentage,

                        "status":
                            overall_status,
                    },

                    "gamification": {

                        "xp":
                            profile.xp,

                        "level":
                            profile.level,

                        "current_streak":
                            profile.current_streak,

                        "best_streak":
                            profile.best_streak,
                    },

                    "leaderboard": {

                        "participating":
                            profile.participate_leaderboard,
                    },

                    "attendance":
                        attendance,

                    "updated_at":
                        data.get(
                            "updated_at"
                        ),
                },

                status=status.HTTP_200_OK,
            )

        # ======================================================
        # PROFILE NOT FOUND
        # ======================================================

        except Profile.DoesNotExist:

            return Response(
                {
                    "message": "Profile not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ======================================================
        # OTHER ERROR
        # ======================================================

        except Exception as e:
            print("\n========== DASHBOARD ERROR ==========")
            print(str(e))
            traceback.print_exc()
            print("=====================================\n")

            return Response(
                {
                    "message": "Failed to load dashboard."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==========================================================
# LEADERBOARD
# ==========================================================

class LeaderboardView(APIView):
    """
    Returns public leaderboard rankings.
    Roll numbers and private attendance details are never returned.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = (
            Profile.objects.filter(participate_leaderboard=True)
            .order_by("-xp", "-level", "-current_streak")
        )

        leaderboard_data = []
        for rank, prof in enumerate(profiles, start=1):
            nickname = prof.nickname.strip() or f"Student-{prof.id}"
            leaderboard_data.append({
                "rank": rank,
                "nickname": nickname,
                "xp": prof.xp,
                "level": prof.level,
                "current_streak": prof.current_streak,
                "is_current_user": prof.user_id == request.user.id,
            })

        # Also indicate if current user participates
        user_profile = Profile.objects.filter(user=request.user).first()
        user_participates = user_profile.participate_leaderboard if user_profile else False

        return Response({
            "leaderboard": leaderboard_data,
            "user_participating": user_participates,
        }, status=status.HTTP_200_OK)


# ==========================================================
# CHALLENGES & BADGES
# ==========================================================

class ChallengesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        challenges = Challenge.objects.filter(active=True)
        completed_ids = set(
            UserChallenge.objects.filter(
                user=request.user, completed=True
            ).values_list("challenge_id", flat=True)
        )

        data = []
        for c in challenges:
            data.append({
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "xp_reward": c.xp_reward,
                "completed": c.id in completed_ids,
            })

        return Response(data, status=status.HTTP_200_OK)


class BadgesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        badges = Badge.objects.all()
        earned_badges = {
            ub.badge_id: ub.earned_at
            for ub in UserBadge.objects.filter(user=request.user)
        }

        data = []
        for b in badges:
            earned = b.id in earned_badges
            data.append({
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "xp_reward": b.xp_reward,
                "earned": earned,
                "earned_at": earned_badges.get(b.id),
            })

        return Response(data, status=status.HTTP_200_OK)


# ==========================================================
# GEMS ON-DEMAND SYNC
# ==========================================================

class SyncAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Runs GEMS scraper on-demand using current student's roll number
        and the provided GEMS password.
        Never stores GEMS password in database or response.
        """
        gems_password = request.data.get("password")
        if not gems_password:
            return Response(
                {"message": "GEMS password is required to sync."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roll_number = request.user.username
        try:
            import asyncio
            from attendance.services.gems_service import get_gems_attendance

            # 1. Fetch current cached attendance for delta calculation
            prev_cache = get_cached_attendance(roll_number)
            prev_attendance = prev_cache.get("attendance", []) if prev_cache else []

            prev_attended = sum(int(item.get("attended", 0)) for item in prev_attendance)
            prev_total = sum(int(item.get("total", 0)) for item in prev_attendance)

            # 2. Run GEMS scraper to get latest attendance
            data = asyncio.run(
                get_gems_attendance(username=roll_number, password=gems_password)
            )

            new_attended = sum(int(item.get("attended", 0)) for item in (data or []))
            new_total = sum(int(item.get("total", 0)) for item in (data or []))

            delta_attended = new_attended - prev_attended
            delta_total = new_total - prev_total


            # Update streak and award XP if student attended all new classes
            profile = Profile.objects.filter(user=request.user).first()
            streak_info = {}
            if profile:
                streak_info = profile.record_attendance_update(
                    delta_attended=delta_attended,
                    delta_total=delta_total,
                )

            return Response(
                {
                    "message": "Attendance synced successfully.",
                    "subject_count": len(data) if data else 0,
                    "streak_info": streak_info,
                },
                status=status.HTTP_200_OK,
            )


        except Exception as e:
            print("\n========== SYNC ATTENDANCE ERROR ==========")
            print(str(e))
            traceback.print_exc()
            print("===========================================\n")
            return Response(
                {"message": "Failed to sync attendance from GEMS."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
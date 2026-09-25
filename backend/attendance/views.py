from django.contrib.auth.models import User

from attendance.services.mongodb_service import (
    get_cached_attendance,
    get_cached_timetable,
)

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
        """
        Returns active and completed challenges for the authenticated user,
        along with XP, level, streak, and progress metrics.
        Guarantees user isolation: only request.user data is retrieved.
        """
        from attendance.services.gamification_service import get_user_challenges_and_progress
        data = get_user_challenges_and_progress(request.user)
        return Response(data, status=status.HTTP_200_OK)


class BadgesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns all badges with unlocked/locked status for the authenticated user.
        """
        from attendance.services.gamification_service import initialize_default_challenges_and_badges
        initialize_default_challenges_and_badges()

        badges = Badge.objects.all().order_by("id")
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
        Automatically updates streak, evaluates challenges, awards XP, and unlocks badges.
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
            from attendance.services.gamification_service import evaluate_user_gamification

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
            profile, _ = Profile.objects.get_or_create(user=request.user)
            streak_info = {}
            if delta_total != 0 or delta_attended != 0:
                streak_info = profile.record_attendance_update(
                    delta_attended=delta_attended,
                    delta_total=delta_total,
                )
            else:
                streak_info = {
                    "current_streak": profile.current_streak,
                    "best_streak": profile.best_streak,
                    "pending_classes": profile.pending_classes,
                    "xp_gained": 0,
                }

            # 3. Authoritatively evaluate challenges and badges
            gamification_result = evaluate_user_gamification(
                user=request.user,
                attendance_data=data,
                delta_attended=delta_attended,
                delta_total=delta_total,
            )

            return Response(
                {
                    "message": "Attendance synced successfully.",
                    "subject_count": len(data) if data else 0,
                    "streak_info": streak_info,
                    "gamification": gamification_result,
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


# ==========================================================
# ATTENDANCE PLANNER
# ==========================================================

class AttendancePlannerView(APIView):
    """
    Returns authenticated student's:
    - current real attendance & overall stats
    - cached timetable
    - next 7 days preview projection (assuming student attends scheduled classes)
    Guarantees user isolation: request.user.username is always used.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import date, timedelta

        roll_number = request.user.username

        # 1. Real attendance from MongoDB
        data = get_cached_attendance(roll_number)
        raw_attendance = data.get("attendance", []) if data else []

        total_attended = 0
        total_classes = 0
        attendance_by_subject = {}

        for item in raw_attendance:
            subj = item.get("subject", "").strip()
            att = int(item.get("attended", 0))
            tot = int(item.get("total", 0))
            perc = round((att / tot) * 100, 2) if tot > 0 else 0.0

            total_attended += att
            total_classes += tot
            attendance_by_subject[subj] = {
                "subject": subj,
                "attended": att,
                "total": tot,
                "percentage": perc,
            }

        overall_perc = round((total_attended / total_classes) * 100, 2) if total_classes > 0 else 0.0

        # 2. Student's timetable
        tt_doc = get_cached_timetable(roll_number)
        timetable = tt_doc.get("timetable", {}) if tt_doc else {}

        # 3. Next 7 days preview
        # Project attendance for the next 7 calendar days starting from tomorrow
        # (or today if classes remain, standard convention: next 7 consecutive days starting from tomorrow)
        # Assuming student attends all scheduled classes on each date
        today = date.today()
        day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

        next_7_days = []
        running_attended = total_attended
        running_total = total_classes

        for i in range(1, 8):
            target_date = today + timedelta(days=i)
            day_name = day_names[target_date.weekday()]
            scheduled_classes = timetable.get(day_name, [])
            class_count = len(scheduled_classes)

            # If student attends scheduled classes on this date:
            projected_attended = running_attended + class_count
            projected_total = running_total + class_count
            projected_perc = (
                round((projected_attended / projected_total) * 100, 2)
                if projected_total > 0
                else 0.0
            )

            next_7_days.append({
                "date": target_date.isoformat(),
                "day_of_week": day_name,
                "class_count": class_count,
                "scheduled_subjects": scheduled_classes,
                "projected_percentage": projected_perc,
                "no_classes": class_count == 0,
            })

            # Advance running baseline so each subsequent day in the preview builds on attending previous days
            running_attended = projected_attended
            running_total = projected_total

        return Response(
            {
                "roll_number": roll_number,
                "overall": {
                    "attended": total_attended,
                    "total": total_classes,
                    "percentage": overall_perc,
                },
                "subjects": list(attendance_by_subject.values()),
                "timetable": timetable,
                "next_7_days": next_7_days,
                "today": today.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


class AttendancePlannerCalculateView(APIView):
    """
    Performs pure WHAT-IF simulation calculation.
    NEVER writes to database or modifies real attendance.
    Strictly uses request.user for student isolation.
    Supports:
    1. 'simulation' mode: selections dictionary { "YYYY-MM-DD": [ {"subject": "...", "status": "present"|"absent"}, ... ] }
    2. 'leave' mode: leave_dates list of date strings [ "YYYY-MM-DD", ... ]
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from datetime import datetime, date

        roll_number = request.user.username

        # 1. Fetch current real baseline from MongoDB
        data = get_cached_attendance(roll_number)
        raw_attendance = data.get("attendance", []) if data else []

        subject_map = {}
        curr_total_attended = 0
        curr_total_conducted = 0

        for item in raw_attendance:
            subj = item.get("subject", "").strip()
            att = int(item.get("attended", 0))
            tot = int(item.get("total", 0))
            curr_total_attended += att
            curr_total_conducted += tot
            subject_map[subj] = {
                "subject": subj,
                "current_attended": att,
                "current_total": tot,
                "simulated_present": 0,
                "simulated_absent": 0,
            }

        curr_overall_perc = (
            round((curr_total_attended / curr_total_conducted) * 100, 2)
            if curr_total_conducted > 0
            else 0.0
        )

        mode = request.data.get("mode", "simulation")  # 'simulation' or 'leave'

        # Fetch timetable for student
        tt_doc = get_cached_timetable(roll_number)
        timetable = tt_doc.get("timetable", {}) if tt_doc else {}
        day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

        total_simulated_present = 0
        total_simulated_absent = 0

        if mode == "leave":
            # Leave mode: list of selected date strings
            leave_dates = request.data.get("leave_dates", [])
            valid_leave_days_count = 0
            classes_missed = 0
            breakdown_by_date = []

            for d_str in set(leave_dates):
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d").date()
                except ValueError:
                    continue

                day_abbr = day_names[dt.weekday()]
                classes_on_day = timetable.get(day_abbr, [])

                if classes_on_day:
                    valid_leave_days_count += 1
                    for subj in classes_on_day:
                        classes_missed += 1
                        total_simulated_absent += 1
                        if subj in subject_map:
                            subject_map[subj]["simulated_absent"] += 1
                        else:
                            subject_map[subj] = {
                                "subject": subj,
                                "current_attended": 0,
                                "current_total": 0,
                                "simulated_present": 0,
                                "simulated_absent": 1,
                            }
                    breakdown_by_date.append({
                        "date": d_str,
                        "day": day_abbr,
                        "classes_missed": len(classes_on_day),
                        "subjects": classes_on_day,
                    })

            new_attended = curr_total_attended
            new_total = curr_total_conducted + classes_missed
            projected_perc = (
                round((new_attended / new_total) * 100, 2)
                if new_total > 0
                else 0.0
            )
            change = round(projected_perc - curr_overall_perc, 2)

            return Response({
                "mode": "leave",
                "current_attendance": curr_overall_perc,
                "projected_attendance": projected_perc,
                "change": change,
                "selected_leave_days": len(set(leave_dates)),
                "effective_leave_days": valid_leave_days_count,
                "classes_missed": classes_missed,
                "current_attended": curr_total_attended,
                "current_total": curr_total_conducted,
                "final_attended": new_attended,
                "final_total": new_total,
                "breakdown": breakdown_by_date,
            }, status=status.HTTP_200_OK)

        else:
            # Multi-date simulation mode:
            # selections = { "YYYY-MM-DD": [ {"subject": "DBMS", "choice": "present"|"absent"}, ... ] }
            selections = request.data.get("selections", {})

            for d_str, class_choices in selections.items():
                if not isinstance(class_choices, list):
                    continue
                for c in class_choices:
                    subj = c.get("subject", "").strip()
                    choice = c.get("choice", "").lower().strip()
                    if not subj or choice not in ["present", "absent"]:
                        continue

                    if choice == "present":
                        total_simulated_present += 1
                        if subj in subject_map:
                            subject_map[subj]["simulated_present"] += 1
                        else:
                            subject_map[subj] = {
                                "subject": subj,
                                "current_attended": 0,
                                "current_total": 0,
                                "simulated_present": 1,
                                "simulated_absent": 0,
                            }
                    elif choice == "absent":
                        total_simulated_absent += 1
                        if subj in subject_map:
                            subject_map[subj]["simulated_absent"] += 1
                        else:
                            subject_map[subj] = {
                                "subject": subj,
                                "current_attended": 0,
                                "current_total": 0,
                                "simulated_present": 0,
                                "simulated_absent": 1,
                            }

            final_attended = curr_total_attended + total_simulated_present
            final_total = curr_total_conducted + total_simulated_present + total_simulated_absent
            projected_perc = (
                round((final_attended / final_total) * 100, 2)
                if final_total > 0
                else 0.0
            )
            # Ensure cap between 0 and 100
            projected_perc = max(0.0, min(100.0, projected_perc))
            change = round(projected_perc - curr_overall_perc, 2)

            # Build subject breakdown
            subjects_result = []
            for s_name, s_data in subject_map.items():
                s_new_att = s_data["current_attended"] + s_data["simulated_present"]
                s_new_tot = s_data["current_total"] + s_data["simulated_present"] + s_data["simulated_absent"]
                s_curr_perc = (
                    round((s_data["current_attended"] / s_data["current_total"]) * 100, 2)
                    if s_data["current_total"] > 0
                    else 0.0
                )
                s_new_perc = (
                    round((s_new_att / s_new_tot) * 100, 2)
                    if s_new_tot > 0
                    else 0.0
                )
                subjects_result.append({
                    "subject": s_name,
                    "current_attended": s_data["current_attended"],
                    "current_total": s_data["current_total"],
                    "current_percentage": s_curr_perc,
                    "simulated_present": s_data["simulated_present"],
                    "simulated_absent": s_data["simulated_absent"],
                    "projected_attended": s_new_att,
                    "projected_total": s_new_tot,
                    "projected_percentage": max(0.0, min(100.0, s_new_perc)),
                })

            return Response({
                "mode": "simulation",
                "current_attendance": curr_overall_perc,
                "projected_attendance": projected_perc,
                "change": change,
                "current_attended": curr_total_attended,
                "current_total": curr_total_conducted,
                "simulated_present": total_simulated_present,
                "simulated_absent": total_simulated_absent,
                "final_attended": final_attended,
                "final_total": final_total,
                "subjects": subjects_result,
            }, status=status.HTTP_200_OK)

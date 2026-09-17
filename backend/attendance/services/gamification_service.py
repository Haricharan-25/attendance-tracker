from datetime import datetime, timezone
from django.db import transaction
from attendance.models import Profile, Challenge, UserChallenge, Badge, UserBadge


# ==========================================================
# DEFAULT DEFINITIONS (CHALLENGES & BADGES)
# ==========================================================

DEFAULT_CHALLENGES = [
    {
        "challenge_type": "streak_3",
        "title": "3-Day Streak",
        "description": "Maintain your attendance goal for 3 consecutive days.",
        "target": 3.0,
        "xp_reward": 20,
    },
    {
        "challenge_type": "streak_7",
        "title": "7-Day Streak",
        "description": "Maintain your attendance goal for 7 consecutive days.",
        "target": 7.0,
        "xp_reward": 100,
    },
    {
        "challenge_type": "overall_75",
        "title": "75% Club",
        "description": "Reach 75% overall attendance.",
        "target": 75.0,
        "xp_reward": 100,
    },
    {
        "challenge_type": "overall_80",
        "title": "80% Club",
        "description": "Reach 80% overall attendance.",
        "target": 80.0,
        "xp_reward": 150,
    },
    {
        "challenge_type": "perfect_week",
        "title": "Perfect Week",
        "description": "Attend all your classes for one week.",
        "target": 1.0,
        "xp_reward": 100,
    },
    {
        "challenge_type": "subject_saver",
        "title": "Subject Saver",
        "description": "Improve a subject's attendance by attending your upcoming classes.",
        "target": 3.0,
        "xp_reward": 75,
    },
]

DEFAULT_BADGES = [
    {
        "name": "First Sync",
        "description": "Successfully synced attendance with GEMS for the first time.",
        "xp_reward": 50,
    },
    {
        "name": "75% Club",
        "description": "Reached 75% overall attendance milestone.",
        "xp_reward": 100,
    },
    {
        "name": "80% Club",
        "description": "Reached 80% overall attendance milestone.",
        "xp_reward": 150,
    },
    {
        "name": "Perfect Week",
        "description": "Attended 100% of classes during a week.",
        "xp_reward": 100,
    },
    {
        "name": "7-Day Streak",
        "description": "Maintained attendance streak for 7 consecutive days.",
        "xp_reward": 100,
    },
    {
        "name": "30-Day Streak",
        "description": "Maintained an epic attendance streak for 30 consecutive days.",
        "xp_reward": 250,
    },
    {
        "name": "Comeback",
        "description": "Recovered a low subject attendance back to safety.",
        "xp_reward": 100,
    },
]


def initialize_default_challenges_and_badges():
    """
    Safely and idempotently initializes the 6 required challenges and 7 badges in the DB.
    Does not duplicate or overwrite existing custom configurations.
    """
    for ch_data in DEFAULT_CHALLENGES:
        challenge = Challenge.objects.filter(challenge_type=ch_data["challenge_type"]).first()
        if not challenge:
            # Also check by title
            challenge = Challenge.objects.filter(title=ch_data["title"]).first()
        
        if challenge:
            challenge.challenge_type = ch_data["challenge_type"]
            challenge.target = ch_data["target"]
            challenge.xp_reward = ch_data["xp_reward"]
            challenge.description = ch_data["description"]
            challenge.title = ch_data["title"]
            challenge.active = True
            challenge.save()
        else:
            Challenge.objects.create(
                challenge_type=ch_data["challenge_type"],
                title=ch_data["title"],
                description=ch_data["description"],
                target=ch_data["target"],
                xp_reward=ch_data["xp_reward"],
                active=True,
            )

    for b_data in DEFAULT_BADGES:
        badge = Badge.objects.filter(name=b_data["name"]).first()
        if badge:
            badge.description = b_data["description"]
            badge.xp_reward = b_data["xp_reward"]
            badge.save()
        else:
            Badge.objects.create(
                name=b_data["name"],
                description=b_data["description"],
                xp_reward=b_data["xp_reward"],
            )


def select_subject_for_saver(attendance_list):
    """
    Picks the most eligible subject for Subject Saver.
    Prefers subjects with percentage < 75% (lowest first).
    If all >= 75%, picks the one closest to 75% or lowest overall.
    """
    if not attendance_list:
        return None

    # Filter subjects with valid classes
    valid = [item for item in attendance_list if item.get("total", 0) > 0]
    if not valid:
        return attendance_list[0] if attendance_list else None

    # Sort by percentage ascending
    sorted_subs = sorted(valid, key=lambda x: (float(x.get("percentage", 100)), x.get("total", 0)))
    return sorted_subs[0]


def ensure_user_challenges(user, attendance_list=None):
    """
    Ensures the user has a UserChallenge instance for each active Challenge.
    Initializes targets and subject baselines if needed.
    """
    initialize_default_challenges_and_badges()
    active_challenges = Challenge.objects.filter(active=True)

    for ch in active_challenges:
        uc, created = UserChallenge.objects.get_or_create(
            user=user,
            challenge=ch,
            defaults={
                "target": ch.target,
                "progress": 0.0,
                "completed": False,
            }
        )

        # If it's a subject saver and has no assigned subject yet
        if ch.challenge_type == "subject_saver" and not uc.subject_name and attendance_list:
            chosen = select_subject_for_saver(attendance_list)
            if chosen:
                uc.subject_name = chosen.get("subject", "")
                uc.baseline_attended = int(chosen.get("attended", 0))
                uc.baseline_total = int(chosen.get("total", 0))
                uc.target = ch.target
                uc.save(update_fields=["subject_name", "baseline_attended", "baseline_total", "target"])


def unlock_badge_if_eligible(user, badge_name, profile=None):
    """
    Unlocks a badge for a user if not already earned.
    Awards badge XP and updates profile.
    Returns (unlocked: bool, badge: Badge).
    """
    badge = Badge.objects.filter(name=badge_name).first()
    if not badge:
        return False, None

    user_badge, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    if created:
        if profile is None:
            profile, _ = Profile.objects.get_or_create(user=user)
        if badge.xp_reward > 0:
            profile.xp += badge.xp_reward
            profile.level = profile.calculate_level()
            profile.save(update_fields=["xp", "level"])
        return True, badge

    return False, badge


def evaluate_user_gamification(user, attendance_data, delta_attended=0, delta_total=0):
    """
    Authoritative server-side evaluation of challenges, XP awards, and badges.
    Called on every sync attendance event.
    Guarantees:
    - XP for any challenge is awarded only once (xp_awarded = True).
    - Streak increases are validated.
    - Badges are awarded only once.
    """
    ensure_user_challenges(user, attendance_data)
    profile, _ = Profile.objects.get_or_create(user=user)

    attendance_list = attendance_data or []
    total_attended = sum(int(item.get("attended", 0)) for item in attendance_list)
    total_classes = sum(int(item.get("total", 0)) for item in attendance_list)
    overall_perc = round((total_attended / total_classes * 100), 2) if total_classes > 0 else 0.0

    now = datetime.now(timezone.utc)
    newly_completed_challenges = []
    newly_unlocked_badges = []
    total_xp_gained = 0

    # 1. Unlock First Sync badge if attendance data is synced
    if attendance_list:
        unlocked, b = unlock_badge_if_eligible(user, "First Sync", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward


    # 2. Evaluate all UserChallenges for this user
    user_challenges = UserChallenge.objects.filter(user=user).select_related("challenge")

    with transaction.atomic():
        for uc in user_challenges:
            ch = uc.challenge
            ch_type = ch.challenge_type
            already_completed = uc.completed

            # -----------------------------------------------
            # STREAK 3-DAY
            # -----------------------------------------------
            if ch_type == "streak_3":
                uc.target = 3.0
                effective_streak = max(profile.current_streak, profile.best_streak)
                uc.progress = min(float(effective_streak), 3.0)
                if uc.progress >= 3.0 and not uc.completed:
                    uc.completed = True
                    uc.completed_at = now

            # -----------------------------------------------
            # STREAK 7-DAY
            # -----------------------------------------------
            elif ch_type == "streak_7":
                uc.target = 7.0
                effective_streak = max(profile.current_streak, profile.best_streak)
                uc.progress = min(float(effective_streak), 7.0)
                if uc.progress >= 7.0 and not uc.completed:
                    uc.completed = True
                    uc.completed_at = now

            # -----------------------------------------------
            # 75% CLUB
            # -----------------------------------------------
            elif ch_type == "overall_75":
                uc.target = 75.0
                uc.progress = round(float(overall_perc), 1)
                if overall_perc >= 75.0 and total_classes > 0 and not uc.completed:
                    uc.completed = True
                    uc.completed_at = now

            # -----------------------------------------------
            # 80% CLUB
            # -----------------------------------------------
            elif ch_type == "overall_80":
                uc.target = 80.0
                uc.progress = round(float(overall_perc), 1)
                if overall_perc >= 80.0 and total_classes > 0 and not uc.completed:
                    uc.completed = True
                    uc.completed_at = now

            # -----------------------------------------------
            # PERFECT WEEK
            # -----------------------------------------------
            elif ch_type == "perfect_week":
                uc.target = 1.0
                # Qualifying condition: streak >= 5 or (delta_total >= 5 and delta_attended == delta_total)
                # Or student has perfect 100% attendance across all subjects with at least 5 classes
                qualifying = False
                if profile.current_streak >= 5 or profile.best_streak >= 5:
                    qualifying = True
                elif delta_total >= 4 and delta_attended >= delta_total:
                    qualifying = True
                elif total_classes >= 5 and overall_perc >= 100.0:
                    qualifying = True

                if qualifying:
                    uc.progress = 1.0
                    if not uc.completed:
                        uc.completed = True
                        uc.completed_at = now
                else:
                    # Partial progress proportional to current streak out of 5
                    uc.progress = round(min(profile.current_streak / 5.0, 0.9), 2)

            # -----------------------------------------------
            # SUBJECT SAVER
            # -----------------------------------------------
            elif ch_type == "subject_saver":
                uc.target = 3.0
                # If no subject is assigned, assign one
                if not uc.subject_name:
                    chosen = select_subject_for_saver(attendance_list)
                    if chosen:
                        uc.subject_name = chosen.get("subject", "")
                        uc.baseline_attended = int(chosen.get("attended", 0))
                        uc.baseline_total = int(chosen.get("total", 0))

                # Check progress on the assigned subject
                if uc.subject_name:
                    current_item = next(
                        (it for it in attendance_list if it.get("subject", "").strip().lower() == uc.subject_name.strip().lower()),
                        None
                    )
                    if current_item:
                        cur_att = int(current_item.get("attended", 0))
                        cur_tot = int(current_item.get("total", 0))
                        # Classes attended since baseline
                        attended_gain = max(0, cur_att - uc.baseline_attended)
                        total_gain = max(0, cur_tot - uc.baseline_total)

                        # If classes were missed since baseline (total_gain > attended_gain), reset gain baseline to current
                        if total_gain > attended_gain and attended_gain < int(uc.target):
                            # Missed a class: reset progress counter from today
                            uc.baseline_attended = cur_att
                            uc.baseline_total = cur_tot
                            attended_gain = 0

                        uc.progress = min(float(attended_gain), uc.target)
                        if uc.progress >= uc.target and not uc.completed:
                            uc.completed = True
                            uc.completed_at = now

            # Award XP if newly completed
            if uc.completed and not uc.xp_awarded:
                uc.xp_awarded = True
                profile.xp += ch.xp_reward
                total_xp_gained += ch.xp_reward
                newly_completed_challenges.append(ch.title)

            uc.save()

        # Update profile level
        profile.level = profile.calculate_level()
        profile.save(update_fields=["xp", "level"])

    # 3. Unlock Attendance & Streak Badges
    if overall_perc >= 75.0 and total_classes > 0:
        unlocked, b = unlock_badge_if_eligible(user, "75% Club", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward

    if overall_perc >= 80.0 and total_classes > 0:
        unlocked, b = unlock_badge_if_eligible(user, "80% Club", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward

    effective_streak = max(profile.current_streak, profile.best_streak)
    if effective_streak >= 7:
        unlocked, b = unlock_badge_if_eligible(user, "7-Day Streak", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward

    if effective_streak >= 30:
        unlocked, b = unlock_badge_if_eligible(user, "30-Day Streak", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward

    # Perfect Week Badge
    perf_week_chal = UserChallenge.objects.filter(
        user=user, challenge__challenge_type="perfect_week", completed=True
    ).exists()
    if perf_week_chal:
        unlocked, b = unlock_badge_if_eligible(user, "Perfect Week", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward

    # Comeback Badge: any subject previously critical (<65%) now >= 75%
    # or Subject Saver completed
    sub_saver_done = UserChallenge.objects.filter(
        user=user, challenge__challenge_type="subject_saver", completed=True
    ).exists()
    if sub_saver_done or (overall_perc >= 75.0 and profile.current_streak >= 3):
        unlocked, b = unlock_badge_if_eligible(user, "Comeback", profile=profile)
        if unlocked:
            newly_unlocked_badges.append(b.name)
            total_xp_gained += b.xp_reward

    # Reload profile for final gamification state
    profile.refresh_from_db()

    return {
        "xp_gained": total_xp_gained,
        "new_xp": profile.xp,
        "new_level": profile.level,
        "current_streak": profile.current_streak,
        "newly_completed_challenges": newly_completed_challenges,
        "newly_unlocked_badges": newly_unlocked_badges,
    }


def get_user_challenges_and_progress(user):
    """
    Prepares active and completed challenges payload formatted for the frontend.
    Strictly scoped to request.user.
    """
    from attendance.services.mongodb_service import get_cached_attendance

    # Make sure default challenges exist and user has records
    cached = get_cached_attendance(user.username)
    att_data = cached.get("attendance", []) if cached else []
    ensure_user_challenges(user, att_data)

    profile, _ = Profile.objects.get_or_create(user=user)
    level_info = profile.get_level_progress()

    user_challenges = (
        UserChallenge.objects.filter(user=user, challenge__active=True)
        .select_related("challenge")
        .order_by("challenge_id")
    )

    active_list = []
    completed_list = []

    for uc in user_challenges:
        ch = uc.challenge
        target = uc.target if uc.target > 0 else (ch.target if ch.target > 0 else 1.0)
        progress = uc.progress

        if uc.completed:
            perc = 100.0
        else:
            perc = round(min((progress / target) * 100.0, 100.0), 1) if target > 0 else 0.0

        item = {
            "id": uc.id,
            "challenge_id": ch.id,
            "name": ch.title,
            "title": ch.title,
            "description": ch.description,
            "challenge_type": ch.challenge_type,
            "target": target,
            "progress": progress,
            "progress_percentage": perc,
            "reward_xp": ch.xp_reward,
            "completed": uc.completed,
            "completed_at": uc.completed_at,
            "subject": uc.subject_name or None,
        }

        if uc.completed:
            completed_list.append(item)
        else:
            active_list.append(item)

    return {
        "user_progress": {
            "level": level_info["level"],
            "xp": level_info["xp"],
            "min_xp": level_info["min_xp"],
            "next_level_xp": level_info["next_level_xp"],
            "streak": profile.current_streak,
            "best_streak": profile.best_streak,
        },
        "active": active_list,
        "completed": completed_list,
    }

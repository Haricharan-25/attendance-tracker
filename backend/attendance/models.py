from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )


    # Public name for leaderboard
    nickname = models.CharField(
        max_length=50,
        blank=True
    )

    # Leaderboard
    participate_leaderboard = models.BooleanField(
        default=False
    )

    # Gamification
    xp = models.PositiveIntegerField(
        default=0
    )

    level = models.PositiveIntegerField(
        default=1
    )

    # Attendance streak
    current_streak = models.PositiveIntegerField(
        default=0
    )

    best_streak = models.PositiveIntegerField(
        default=0
    )

    # Lag tolerance for GEMS delayed updates
    pending_classes = models.PositiveIntegerField(
        default=0
    )

    last_streak_date = models.DateField(
        null=True,
        blank=True
    )

    def calculate_level(self):
        if self.xp >= 1000:
            return 5 + (self.xp - 1000) // 500
        elif self.xp >= 500:
            return 4
        elif self.xp >= 250:
            return 3
        elif self.xp >= 100:
            return 2
        else:
            return 1

    def get_level_progress(self):
        """
        Returns level info with progress towards next level.
        """
        lvl = self.calculate_level()
        thresholds = [
            (1, 0, 100),
            (2, 100, 250),
            (3, 250, 500),
            (4, 500, 1000),
        ]
        if lvl <= 4:
            for l_num, min_xp, max_xp in thresholds:
                if lvl == l_num:
                    return {
                        "level": lvl,
                        "xp": self.xp,
                        "min_xp": min_xp,
                        "next_level_xp": max_xp,
                    }
        # For Level 5 and above:
        base_lvl5 = 1000 + (lvl - 5) * 500
        return {
            "level": lvl,
            "xp": self.xp,
            "min_xp": base_lvl5,
            "next_level_xp": base_lvl5 + 500,
        }

    def record_attendance_update(self, delta_attended, delta_total):
        """
        Lag-Tolerant Streak Engine:
        Accommodates GEMS's behavior where total increases today, but attended is credited tomorrow.

        - If delta_attended == delta_total > 0:
            Student immediately attended all new classes -> streak += 1, +25 XP
            Clear any pending classes.

        - If delta_total > 0 and delta_attended == 0:
            Classes were held today. Total incremented, attended pending for next day.
            Mark pending_classes += delta_total. Keep streak intact.

        - If delta_attended > 0 and delta_total == 0 (or delta_attended > delta_total):
            Attended counts arrived from previous day's classes!
            Satisfies pending_classes -> streak += 1, +25 XP
            Deduct from pending_classes.

        - If new total arrives and attended STILL didn't increase after pending window:
            An actual absence is confirmed -> reset current_streak to 0.
        """
        from datetime import date
        today = date.today()
        xp_gained = 0

        # Case A: Both increased equally (same day or batch complete)
        if delta_total > 0 and delta_attended >= delta_total:
            self.current_streak += 1
            xp_gained = 25
            self.pending_classes = 0
            self.last_streak_date = today

        # Case B: Attended caught up from yesterday's pending classes
        elif delta_attended > 0 and delta_attended >= self.pending_classes:
            self.current_streak += 1
            xp_gained = 25
            self.pending_classes = max(0, self.pending_classes - delta_attended)
            self.last_streak_date = today

        # Case C: Total increased today, but attended hasn't been credited yet by GEMS
        elif delta_total > 0 and delta_attended < delta_total:
            if self.pending_classes > 0 and self.last_streak_date != today:
                # Previous pending classes were never attended -> Confirmed absence!
                self.current_streak = 0
                self.pending_classes = delta_total
                self.last_streak_date = today
            else:
                # First time seeing today's class: give GEMS the 24-hour buffer
                self.pending_classes += (delta_total - delta_attended)
                self.last_streak_date = today

        if self.current_streak > self.best_streak:
            self.best_streak = self.current_streak

        if xp_gained > 0:
            self.xp += xp_gained
            self.level = self.calculate_level()

        self.save(
            update_fields=[
                "current_streak",
                "best_streak",
                "pending_classes",
                "last_streak_date",
                "xp",
                "level",
            ]
        )
        return {
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "pending_classes": self.pending_classes,
            "xp_gained": xp_gained,
        }



    def __str__(self):
        return self.user.username


class Subject(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subjects"
    )

    name = models.CharField(
        max_length=100
    )

    code = models.CharField(
        max_length=30,
        blank=True
    )

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class AttendanceRecord(models.Model):

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("holiday", "Holiday"),
        ("no_class", "No Class"),
    ]

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-date"]

        unique_together = (
            "subject",
            "date",
        )

    def __str__(self):
        return (
            f"{self.subject.name} - "
            f"{self.date} - "
            f"{self.status}"
        )


class Badge(models.Model):
    name = models.CharField(
        max_length=100
    )

    description = models.TextField()

    xp_reward = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="badges"
    )

    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE
    )

    earned_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = (
            "user",
            "badge",
        )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.badge.name}"
        )


class Challenge(models.Model):
    CHALLENGE_TYPE_CHOICES = [
        ("streak_3", "3-Day Streak"),
        ("streak_7", "7-Day Streak"),
        ("overall_75", "75% Club"),
        ("overall_80", "80% Club"),
        ("perfect_week", "Perfect Week"),
        ("subject_saver", "Subject Saver"),
        ("custom", "Custom Challenge"),
    ]

    title = models.CharField(
        max_length=150
    )

    description = models.TextField()

    challenge_type = models.CharField(
        max_length=50,
        choices=CHALLENGE_TYPE_CHOICES,
        default="custom"
    )

    target = models.FloatField(
        default=0.0
    )

    xp_reward = models.PositiveIntegerField(
        default=0
    )

    active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    @property
    def name(self):
        return self.title

    def __str__(self):
        return self.title


class UserChallenge(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="challenges"
    )

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE
    )

    progress = models.FloatField(
        default=0.0
    )

    target = models.FloatField(
        default=0.0
    )

    subject_name = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    baseline_attended = models.PositiveIntegerField(
        default=0
    )

    baseline_total = models.PositiveIntegerField(
        default=0
    )

    completed = models.BooleanField(
        default=False
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    xp_awarded = models.BooleanField(
        default=False
    )

    class Meta:
        unique_together = (
            "user",
            "challenge",
        )

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} ({'Done' if self.completed else 'Active'})"
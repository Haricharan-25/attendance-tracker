from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Profile


class RegisterSerializer(serializers.ModelSerializer):

    # Roll number will become the Django username
    roll_number = serializers.CharField(
        required=True,
        max_length=50
    )

    password = serializers.CharField(
        write_only=True,
        min_length=6
    )

    nickname = serializers.CharField(
        required=False,
        allow_blank=True
    )

    participate_leaderboard = serializers.BooleanField(
        default=False
    )

    class Meta:
        model = User

        fields = [
            "roll_number",
            "password",
            "nickname",
            "participate_leaderboard",
        ]

    def validate_roll_number(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Roll number is required."
            )

        # One account per roll number
        if User.objects.filter(
            username=value
        ).exists():

            raise serializers.ValidationError(
                "This roll number is already registered."
            )

        return value

    def validate(self, attrs):

        participate = attrs.get(
            "participate_leaderboard",
            False
        )

        nickname = attrs.get(
            "nickname",
            ""
        ).strip()

        # Nickname is required only for leaderboard users
        if participate and not nickname:

            raise serializers.ValidationError({
                "nickname":
                "Nickname is required to participate in the leaderboard."
            })

        return attrs

    def create(self, validated_data):

        roll_number = validated_data.pop(
            "roll_number"
        ).strip()

        password = validated_data.pop(
            "password"
        )

        nickname = validated_data.pop(
            "nickname",
            ""
        ).strip()

        participate = validated_data.pop(
            "participate_leaderboard",
            False
        )

        # Roll number becomes Django username
        user = User.objects.create_user(
            username=roll_number,
            password=password,
        )

        # Profile is automatically created
        # by the post_save signal.
        profile = Profile.objects.get(
            user=user
        )

        # Save leaderboard information
        profile.nickname = (
            nickname
            if nickname
            else user.username
        )

        profile.participate_leaderboard = participate

        profile.save()

        return user


class ProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    class Meta:
        model = Profile

        fields = [
            "username",
            "nickname",
            "participate_leaderboard",
            "xp",
            "level",
            "current_streak",
            "best_streak",
        ]

        read_only_fields = [
            "username",
            "xp",
            "level",
            "current_streak",
            "best_streak",
        ]


class LeaderboardSerializer(serializers.ModelSerializer):
    """
    Public leaderboard representation.
    Strictly excludes user id, roll number, email, and private attendance data.
    """
    class Meta:
        model = Profile
        fields = [
            "nickname",
            "xp",
            "level",
            "current_streak",
        ]
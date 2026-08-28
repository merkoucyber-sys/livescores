
from django.core.exceptions import ValidationError
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(
        upload_to="teams/",
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def logo_url(self):
        """
        Returns the team logo URL if a logo exists.
        """
        if self.logo:
            return self.logo.url
        return ""


class Match(models.Model):

    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("live", "Live"),
        ("finished", "Finished"),
    ]

    ROUND_CHOICES = [
        ("league", "League"),
        ("semi_final", "Semi-Final"),
        ("final", "Final"),
        ("friendly", "Friendly"),
    ]

    home_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="home_matches"
    )

    away_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="away_matches"
    )

    date = models.DateField()

    kickoff = models.TimeField()

    venue = models.CharField(
        max_length=150,
        default="Parua Green Stadium"
    )

    round_name = models.CharField(
        max_length=30,
        choices=ROUND_CHOICES,
        default="league"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="upcoming"
    )

    home_score = models.PositiveIntegerField(default=0)
    away_score = models.PositiveIntegerField(default=0)

    home_penalty_score = models.PositiveIntegerField(default=0)
    away_penalty_score = models.PositiveIntegerField(default=0)

    half_time_home_score = models.PositiveIntegerField(default=0)
    half_time_away_score = models.PositiveIntegerField(default=0)

    first_half_added_minutes = models.PositiveIntegerField(default=0)
    second_half_added_minutes = models.PositiveIntegerField(default=0)

    clock_seconds = models.PositiveIntegerField(default=0)

    clock_running = models.BooleanField(default=False)

    winner = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wins"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "kickoff"]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["date", "kickoff"]),
            models.Index(fields=["status", "date"]),
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

    def clean(self):
        """
        Prevent invalid matches.
        """

        if self.home_team == self.away_team:
            raise ValidationError(
                "Home team and away team cannot be the same."
            )

        if self.winner is not None:
            if self.winner.pk not in [
                self.home_team.pk,
                self.away_team.pk,
            ]:
                raise ValidationError(
                    "Winner must be one of the teams in this match."
                )

        if self.status == "live" and self.winner is not None:
            raise ValidationError(
                "A live match cannot have a winner yet."
            )

        if self.status == "finished" and self.home_score == self.away_score:
            if self.home_penalty_score == self.away_penalty_score and self.winner:
                raise ValidationError(
                    "A drawn match needs different penalty scores to have a winner."
                )

    def save(self, *args, **kwargs):
        if self.status == "finished":
            if self.home_score > self.away_score:
                self.winner = self.home_team
            elif self.away_score > self.home_score:
                self.winner = self.away_team
            elif self.home_penalty_score > self.away_penalty_score:
                self.winner = self.home_team
            elif self.away_penalty_score > self.home_penalty_score:
                self.winner = self.away_team
            else:
                self.winner = None
        else:
            self.winner = None
        super().save(*args, **kwargs)

    @property
    def clock_display(self):
        """
        Convert seconds into MM:SS.
        """

        minutes = self.clock_seconds // 60
        seconds = self.clock_seconds % 60

        return f"{minutes:02d}:{seconds:02d}"

    @property
    def score_display(self):
        """
        Example: 2 - 1
        """

        return f"{self.home_score} - {self.away_score}"

    @property
    def is_live(self):
        return self.status == "live"

    @property
    def is_finished(self):
        return self.status == "finished"

    @property
    def is_upcoming(self):
        return self.status == "upcoming"

    @property
    def home_logo(self):
        return self.home_team.logo_url

    @property
    def away_logo(self):
        return self.away_team.logo_url


class MatchEvent(models.Model):

    EVENT_CHOICES = [
        ("goal", "Goal"),
        ("yellow", "Yellow Card"),
        ("red", "Red Card"),
        ("sub", "Substitution"),
    ]

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="events"
    )

    minute = models.PositiveIntegerField(default=0)

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_CHOICES
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="match_events"
    )

    player = models.CharField(
        max_length=100,
        blank=True
    )

    player_out = models.CharField(
        max_length=100,
        blank=True
    )

    note = models.CharField(
        max_length=200,
        blank=True
    )

    class Meta:
        ordering = ["minute", "id"]

        indexes = [
            models.Index(fields=["match", "minute"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return (
            f"{self.match} - "
            f"{self.event_type} "
            f"{self.minute}'"
        )

    def save(self, *args, **kwargs):
        match = getattr(self, "match", None)
        if self.minute == 0 and match is not None:
            self.minute = max(1, (match.clock_seconds + 59) // 60)
        super().save(*args, **kwargs)

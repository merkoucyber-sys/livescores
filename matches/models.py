
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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

    PERIOD_CHOICES = [
        ("not_started", "Not started"),
        ("first_half", "First half"),
        ("half_time", "Half time"),
        ("second_half", "Second half"),
        ("full_time", "Full time"),
    ]

    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("live", "Live"),
        ("postponed", "Postponed"),
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

    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default="not_started")

    started_at = models.DateTimeField(null=True, blank=True)

    clock_started_at = models.DateTimeField(null=True, blank=True)

    postponed_at = models.DateTimeField(null=True, blank=True)

    postponement_reason = models.CharField(max_length=250, blank=True)

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
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, "%Y-%m-%d").date()
        if isinstance(self.kickoff, str):
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    self.kickoff = datetime.strptime(self.kickoff, fmt).time()
                    break
                except ValueError:
                    continue

        if self.status == "live" and self.started_at is None:
            scheduled_start = timezone.make_aware(
                timezone.datetime.combine(self.date, self.kickoff),
                timezone.get_current_timezone(),
            )
            self.started_at = scheduled_start
        if self.status == "live" and self.clock_running:
            if self.clock_started_at is None:
                self.clock_started_at = self.started_at or timezone.now()
        if self.status == "postponed":
            if self.clock_started_at is not None and self.clock_running:
                elapsed_seconds = int(
                    (timezone.now() - self.clock_started_at).total_seconds()
                )
                self.clock_seconds += max(0, elapsed_seconds)
            self.clock_running = False
            self.clock_started_at = None
            if self.postponed_at is None:
                self.postponed_at = timezone.now()
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
    def current_clock_seconds(self):
        if self.status != "live" or not self.clock_running:
            return self.clock_seconds
        anchor = self.clock_started_at or self.started_at
        if anchor is None:
            return self.clock_seconds
        elapsed_seconds = max(0, int((timezone.now() - anchor).total_seconds()))
        return self.clock_seconds + elapsed_seconds

    @property
    def clock_display(self):
        """
        Convert seconds into MM:SS.
        """

        minutes = self.current_clock_seconds // 60
        seconds = self.current_clock_seconds % 60

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
    def is_postponed(self):
        return self.status == "postponed"

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
        ("foul", "Foul"),
        ("corner", "Corner"),
    ]

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="events"
    )

    minute = models.PositiveIntegerField(default=0)

    period = models.CharField(
        max_length=20,
        choices=Match.PERIOD_CHOICES,
        blank=True,
        default="",
    )

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
        if match is not None:
            if not self.period:
                self.period = match.period
            if self.minute == 0:
                self.minute = max(1, (match.current_clock_seconds + 59) // 60)

        if match is not None and self.event_type == "goal":
            if self.team_id == match.home_team_id:
                match.home_score += 1
            elif self.team_id == match.away_team_id:
                match.away_score += 1
            match.save(update_fields=["home_score", "away_score"])

        super().save(*args, **kwargs)

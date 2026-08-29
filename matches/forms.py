from django import forms

from .models import Match, MatchEvent, Team


class MatchControlForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = (
            "home_score",
            "away_score",
            "home_penalty_score",
            "away_penalty_score",
            "half_time_home_score",
            "half_time_away_score",
            "clock_seconds",
            "started_at",
            "postponement_reason",
        )
        widgets = {
            "started_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "postponement_reason": forms.TextInput(
                attrs={"placeholder": "Reason for postponement"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.started_at:
            self.initial["started_at"] = self.instance.started_at.strftime(
                "%Y-%m-%dT%H:%M"
            )
        if getattr(self.instance, "status", None) == "finished":
            for field in self.fields.values():
                field.disabled = True


class MatchEventForm(forms.ModelForm):
    minute = forms.IntegerField(required=False, min_value=0)

    class Meta:
        model = MatchEvent
        fields = ("event_type", "team", "minute", "player", "player_out", "note")
        widgets = {
            "minute": forms.NumberInput(attrs={"min": 0, "placeholder": "Auto"}),
            "player": forms.TextInput(attrs={"placeholder": "Player or description"}),
            "player_out": forms.TextInput(attrs={"placeholder": "Player out (substitution)"}),
            "note": forms.TextInput(attrs={"placeholder": "Optional note"}),
        }

    def __init__(self, match, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._match = match
        self.fields["team"].queryset = Team.objects.filter(
            pk__in=(match.home_team_id, match.away_team_id)
        )
        if getattr(match, "status", None) == "finished":
            for field in self.fields.values():
                field.disabled = True

    def clean_minute(self):
        minute = self.cleaned_data.get("minute")
        if minute in (None, 0):
            base_seconds = self._match.current_clock_seconds
            if self._match.period == "second_half":
                base_seconds = max(0, base_seconds - 2700)
            return max(1, (base_seconds + 59) // 60)
        return minute


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ("name", "logo")


class MatchSetupForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = (
            "home_team", "away_team", "date", "kickoff", "venue", "round_name",
        )
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "kickoff": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get("home_team")
        away_team = cleaned_data.get("away_team")
        match_date = cleaned_data.get("date")

        if home_team == away_team:
            raise forms.ValidationError("Choose two different teams.")

        if home_team and away_team and match_date:
            existing_match = Match.objects.filter(
                home_team=home_team,
                away_team=away_team,
                date=match_date,
            )
            if self.instance and self.instance.pk:
                existing_match = existing_match.exclude(pk=self.instance.pk)
            if existing_match.exists():
                raise forms.ValidationError(
                    "A match for these two teams on this date already exists. "
                    "Use Reschedule on the existing match instead of creating a duplicate."
                )

        return cleaned_data

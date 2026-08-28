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


class MatchEventForm(forms.ModelForm):
    class Meta:
        model = MatchEvent
        fields = ("event_type", "team", "minute", "player", "player_out", "note")
        widgets = {
            "minute": forms.NumberInput(attrs={"min": 0, "placeholder": "Minute"}),
            "player": forms.TextInput(attrs={"placeholder": "Player or description"}),
            "player_out": forms.TextInput(attrs={"placeholder": "Player out (substitution)"}),
            "note": forms.TextInput(attrs={"placeholder": "Optional note"}),
        }

    def __init__(self, match, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = Team.objects.filter(
            pk__in=(match.home_team_id, match.away_team_id)
        )


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
        if cleaned_data.get("home_team") == cleaned_data.get("away_team"):
            raise forms.ValidationError("Choose two different teams.")
        return cleaned_data

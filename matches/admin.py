from django.contrib import admin
from .models import Team, Match, MatchEvent

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "home_team", "away_team", "date", "kickoff",
        "status", "home_score", "away_score", "venue", "qualification"
    )
    list_filter = ("status", "date", "round_name")
    list_editable = ("status", "home_score", "away_score")
    search_fields = ("home_team__name", "away_team__name")

    @admin.display(description="Final qualification")
    def qualification(self, match):
        if match.round_name != "semi_final":
            return "-"
        if match.status == "finished" and match.winner:
            return f"Qualified: {match.winner.name}"
        return "Awaiting winner"

@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("match", "minute", "event_type", "team", "player", "player_out")
    list_filter = ("event_type",)
    search_fields = ("player", "player_out", "note")

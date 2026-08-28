from django.contrib import admin
from .models import Team, Match, MatchEvent

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "home_team", "away_team", "date", "kickoff",
        "status", "home_score", "away_score", "played_time", "started_at", "venue", "qualification"
    )
    list_filter = ("status", "date", "round_name")
    list_editable = ("status", "home_score", "away_score")
    search_fields = ("home_team__name", "away_team__name")
    actions = ("mark_postponed",)

    @admin.action(description="Mark selected matches as postponed")
    def mark_postponed(self, request, queryset):
        updated = 0
        for match in queryset:
            match.status = "postponed"
            match.save()
            updated += 1
        self.message_user(request, f"{updated} match(es) marked as postponed.")

    @admin.display(description="Final qualification")
    def qualification(self, match):
        if match.round_name != "semi_final":
            return "-"
        if match.status == "finished" and match.winner:
            return f"Qualified: {match.winner.name}"
        return "Awaiting winner"

    @admin.display(description="Played time")
    def played_time(self, match):
        return match.clock_display

@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("match", "minute", "event_type", "team", "player", "player_out")
    list_filter = ("event_type",)
    search_fields = ("player", "player_out", "note")

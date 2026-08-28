from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Match, Team

def home(request):
    today = timezone.localdate()
    live = Match.objects.filter(status="live").select_related("home_team", "away_team")
    postponed = Match.objects.filter(status="postponed").select_related("home_team", "away_team").order_by("date", "kickoff")[:8]
    upcoming = Match.objects.filter(status="upcoming", date__gte=today).select_related("home_team", "away_team")[:8]
    results = Match.objects.filter(status="finished").select_related("home_team", "away_team").order_by("-date", "-kickoff")[:8]
    final_qualifiers = Team.objects.filter(
        wins__round_name="semi_final",
        wins__status="finished",
    ).distinct().order_by("name")
    return render(request, "home.html", {
        "live": live, "postponed": postponed, "upcoming": upcoming, "results": results,
        "final_qualifiers": final_qualifiers, "today": today
    })

def match_detail(request, pk):
    match = get_object_or_404(
        Match.objects.select_related("home_team", "away_team"), pk=pk
    )
    events = match.events.all()
    return render(request, "match_detail.html", {
        "match": match,
        "goals_count": events.filter(event_type="goal").count(),
        "yellow_count": events.filter(event_type="yellow").count(),
        "red_count": events.filter(event_type="red").count(),
        "substitutions_count": events.filter(event_type="sub").count(),
        "fouls_count": events.filter(event_type="foul").count(),
        "corners_count": events.filter(event_type="corner").count(),
    })

def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team)
    ).select_related("home_team", "away_team", "winner").order_by(
        "-date", "-kickoff"
    )
    events = team.match_events.select_related("match").order_by(
        "-match__date", "-minute"
    )[:20]
    finished_matches = matches.filter(status="finished")
    semi_final_wins = matches.filter(
        round_name="semi_final", status="finished", winner=team
    ).count()
    return render(request, "team_detail.html", {
        "team": team,
        "matches": matches,
        "events": events,
        "finished_count": finished_matches.count(),
        "wins_count": finished_matches.filter(winner=team).count(),
        "semi_final_wins": semi_final_wins,
    })

def live_data(request):
    data = []
    for m in Match.objects.filter(status="live").select_related("home_team", "away_team"):
        data.append({
            "id": m.id,
            "home": m.home_team.name,
            "away": m.away_team.name,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "clock": m.clock_seconds,
            "running": m.clock_running,
        })
    return JsonResponse({"matches": data})

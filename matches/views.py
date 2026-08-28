from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import MatchControlForm, MatchEventForm, MatchSetupForm, TeamForm
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


def control_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("match_control")
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user and user.is_staff:
            login(request, user)
            return redirect(request.POST.get("next") or "match_control")
        messages.error(request, "Invalid staff username or password.")
    return render(request, "control_login.html", {"next": request.GET.get("next", "")})


def control_logout(request):
    logout(request)
    return redirect("control_login")


@staff_member_required(login_url="control_login")
def match_control(request):
    matches = Match.objects.select_related("home_team", "away_team").prefetch_related("events")
    if request.method == "POST":
        match_id = request.POST.get("match_id")
        match = get_object_or_404(Match, pk=match_id) if match_id else None
        action = request.POST.get("action")
        if action == "add_team":
            form = TeamForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Team added.")
        elif action == "add_match":
            form = MatchSetupForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Match created.")
        elif action in {"start", "resume", "postpone", "finish"} and match:
            match_form = MatchControlForm(request.POST, instance=match)
            if match_form.is_valid():
                controlled_match = match_form.save(commit=False)
                controlled_match.status = {
                    "start": "live",
                    "resume": "live",
                    "postpone": "postponed",
                    "finish": "finished",
                }[action]
                controlled_match.save()
                messages.success(request, f"{match} updated: {controlled_match.get_status_display()}.")
            else:
                messages.error(request, "Please correct the match details before saving.")
        elif action == "delete_event" and match:
            event = get_object_or_404(match.events, pk=request.POST.get("event_id"))
            event.delete()
            messages.success(request, "Event deleted.")
        elif action == "event" and match:
            event_form = MatchEventForm(match, request.POST)
            if event_form.is_valid():
                event = event_form.save(commit=False)
                event.match = match
                event.save()
                messages.success(request, f"{event.get_event_type_display()} added to {match}.")
            else:
                messages.error(request, "Please correct the event details before saving.")
        return redirect("match_control")

    match_controls = [
        {
            "match": match,
            "match_form": MatchControlForm(instance=match),
            "event_form": MatchEventForm(match),
        }
        for match in matches
    ]
    return render(request, "match_control.html", {
        "match_controls": match_controls,
        "team_form": TeamForm(),
        "match_setup_form": MatchSetupForm(),
        "teams": Team.objects.all(),
    })

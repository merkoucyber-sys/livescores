from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
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
            "clock": m.current_clock_seconds,
            "running": m.clock_running,
        })
    return JsonResponse({"matches": data})


def control_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("match_control")

    has_staff_user = get_user_model().objects.filter(is_staff=True).exists()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_staff":
            username = (request.POST.get("username") or "").strip()
            password = request.POST.get("password") or ""
            password_confirm = request.POST.get("password_confirm") or ""

            if not username or not password:
                messages.error(request, "Username and password are required.")
            elif password != password_confirm:
                messages.error(request, "Passwords do not match.")
            elif get_user_model().objects.filter(username=username).exists():
                messages.error(request, "That username is already taken.")
            else:
                user = get_user_model().objects.create_user(
                    username=username,
                    password=password,
                    is_staff=True,
                    is_superuser=True,
                )
                login(request, user)
                return redirect(request.POST.get("next") or "match_control")

        else:
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if user and user.is_staff:
                    login(request, user)
                    return redirect(request.POST.get("next") or "match_control")
                form.add_error(None, "Only staff accounts can access the control room.")
            return render(
                request,
                "control_login.html",
                {"form": form, "next": request.GET.get("next", ""), "has_staff_user": has_staff_user},
            )

    form = AuthenticationForm()
    return render(
        request,
        "control_login.html",
        {"form": form, "next": request.GET.get("next", ""), "has_staff_user": has_staff_user},
    )


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
        if match and match.status == "finished" and action in {"start", "resume", "halftime", "postpone", "finish", "reschedule", "event", "delete_event"}:
            messages.error(request, "Finished matches are locked and cannot be edited.")
            return redirect("match_control")
        if action == "add_team":
            form = TeamForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Team added.")
        elif action == "edit_team":
            team = get_object_or_404(Team, pk=request.POST.get("team_id"))
            form = TeamForm(request.POST, request.FILES, instance=team)
            if form.is_valid():
                form.save()
                messages.success(request, "Team updated.")
        elif action == "delete_team":
            team = get_object_or_404(Team, pk=request.POST.get("team_id"))
            if team.home_matches.exists() or team.away_matches.exists():
                messages.error(request, "This team cannot be deleted because it has match history.")
            else:
                team.delete()
                messages.success(request, "Team deleted.")
        elif action == "add_match":
            form = MatchSetupForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Match created.")
        elif action == "reschedule" and match:
            match.status = "upcoming"
            match.period = "not_started"
            match.clock_seconds = 0
            match.clock_running = False
            match.clock_started_at = None
            match.started_at = None
            match.postponed_at = None
            match.postponement_reason = ""
            match.save()
            messages.success(request, f"{match} returned to the schedule as upcoming.")
        elif action == "delete_match" and match:
            match_name = str(match)
            match.delete()
            messages.success(request, f"{match_name} deleted.")
        elif action in {"start", "resume", "halftime", "postpone", "finish"} and match:
            controlled_match = match
            controlled_match.status = {
                "start": "live",
                "resume": "live",
                "halftime": "live",
                "postpone": "postponed",
                "finish": "finished",
            }[action]
            if action == "start":
                controlled_match.period = "first_half"
                started_at_value = request.POST.get("started_at")
                if started_at_value:
                    try:
                        parsed_started_at = timezone.datetime.strptime(
                            started_at_value,
                            "%Y-%m-%dT%H:%M",
                        )
                        controlled_match.started_at = timezone.make_aware(
                            parsed_started_at,
                            timezone.get_current_timezone(),
                        )
                    except ValueError:
                        controlled_match.started_at = controlled_match.started_at or timezone.now()
                elif controlled_match.started_at is None:
                    scheduled_start = timezone.make_aware(
                        timezone.datetime.combine(controlled_match.date, controlled_match.kickoff),
                        timezone.get_current_timezone(),
                    )
                    controlled_match.started_at = scheduled_start
                controlled_match.clock_started_at = controlled_match.started_at
                controlled_match.clock_running = True
            elif action == "halftime":
                if controlled_match.clock_started_at is not None:
                    controlled_match.clock_seconds += max(
                        0,
                        int((timezone.now() - controlled_match.clock_started_at).total_seconds()),
                    )
                controlled_match.period = "half_time"
                controlled_match.clock_running = False
                controlled_match.clock_started_at = None
            elif action == "resume":
                controlled_match.period = "second_half"
                controlled_match.clock_seconds = max(controlled_match.clock_seconds, 2700)
                controlled_match.clock_running = True
                controlled_match.clock_started_at = timezone.now()
            elif action == "finish":
                controlled_match.period = "full_time"
                controlled_match.clock_running = False
            controlled_match.save()
            messages.success(request, f"{match} updated: {controlled_match.get_status_display()}.")
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
    team_controls = [
        {"team": team, "form": TeamForm(instance=team)}
        for team in Team.objects.all()
    ]
    return render(request, "match_control.html", {
        "match_controls": match_controls,
        "team_form": TeamForm(),
        "match_setup_form": MatchSetupForm(),
        "team_controls": team_controls,
    })

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .forms import MatchEventForm
from .models import Match, Team


class MatchControlActionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin",
            password="secret123",
            is_staff=True,
            is_superuser=True,
        )
        self.home_team = Team.objects.create(name="Alpha")
        self.away_team = Team.objects.create(name="Beta")
        self.match = Match.objects.create(
            home_team=self.home_team,
            away_team=self.away_team,
            date="2026-10-20",
            kickoff="18:00:00",
            status="postponed",
            clock_seconds=780,
            clock_running=True,
            period="second_half",
            postponement_reason="Rain",
        )

    def test_reschedule_match_resets_match_back_to_upcoming(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("match_control"),
            {"match_id": self.match.pk, "action": "reschedule"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, "upcoming")
        self.assertEqual(self.match.clock_seconds, 0)
        self.assertFalse(self.match.clock_running)
        self.assertEqual(self.match.period, "not_started")
        self.assertIsNone(self.match.started_at)
        self.assertEqual(self.match.postponement_reason, "")

    def test_delete_match_removes_match_record(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("match_control"),
            {"match_id": self.match.pk, "action": "delete_match"},
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Match.objects.filter(pk=self.match.pk).exists())

    def test_duplicate_fixture_creation_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("match_control"),
            {
                "action": "add_match",
                "home_team": self.home_team.pk,
                "away_team": self.away_team.pk,
                "date": "2026-10-20",
                "kickoff": "18:00",
                "venue": "Parua Green Stadium",
                "round_name": "league",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Match.objects.filter(home_team=self.home_team, away_team=self.away_team, date="2026-10-20").count(), 1)

    def test_first_staff_account_can_be_created_from_login_page(self):
        self.user.delete()

        response = self.client.get(reverse("control_login"))
        self.assertContains(response, "Create first staff account")

        response = self.client.post(
            reverse("control_login"),
            {
                "action": "create_staff",
                "username": "newadmin",
                "password": "StrongPass123",
                "password_confirm": "StrongPass123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            get_user_model().objects.filter(username="newadmin", is_staff=True, is_superuser=True).exists()
        )

    def test_goal_event_minutes_are_filled_automatically(self):
        live_match = Match.objects.create(
            home_team=self.home_team,
            away_team=self.away_team,
            date="2026-10-21",
            kickoff="20:00:00",
            status="live",
            clock_seconds=660,
            clock_running=True,
            period="second_half",
        )
        form = MatchEventForm(
            live_match,
            data={
                "event_type": "goal",
                "team": self.home_team.pk,
                "minute": "",
                "player": "M. Smith",
                "player_out": "",
                "note": "",
            },
        )

        self.assertTrue(form.is_valid())
        event = form.save(commit=False)
        event.match = live_match
        event.save()
        self.assertEqual(event.minute, 11)
        self.assertEqual(live_match.home_score, 1)

    def test_finished_matches_are_not_editable_from_control_room(self):
        finished_match = Match.objects.create(
            home_team=self.home_team,
            away_team=self.away_team,
            date="2026-10-22",
            kickoff="19:00:00",
            status="finished",
            home_score=2,
            away_score=1,
            period="full_time",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("match_control"),
            {
                "match_id": finished_match.pk,
                "action": "start",
                "home_score": 3,
                "away_score": 1,
            },
        )

        self.assertEqual(response.status_code, 302)
        finished_match.refresh_from_db()
        self.assertEqual(finished_match.home_score, 2)
        self.assertEqual(finished_match.away_score, 1)

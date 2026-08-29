from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

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

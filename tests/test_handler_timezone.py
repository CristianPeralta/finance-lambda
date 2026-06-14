"""
Tests that _handle_registro writes dates in Peru timezone (America/Lima),
not in UTC. The bug: when called after 7pm Peru (= midnight UTC), date.today()
in a UTC Lambda would return the NEXT calendar day, causing n8n to never find
matching records and keep sending reminders all night.
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch

# Allow importing from src/ without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import handler


def _make_result(**kwargs):
    defaults = dict(
        tipo="gasto",
        scope="pareja",
        description="test",
        category="comida",
        amount=10.0,
        paid_by="cristian",
        pedido_num=None,
        cliente=None,
        raw="/gasto pareja 10 comida",
        error=None,
        scope_hint=None,
    )
    defaults.update(kwargs)
    return MagicMock(**defaults)


class TestHandlerTimezone:
    """
    The critical moment is right after 7pm Peru (00:00 UTC next day).
    UTC date = D+1, Peru date = D. The Lambda must write D, not D+1.
    """

    def test_pareja_gasto_writes_peru_date_after_7pm(self):
        # Simulate 9:15pm Peru on June 13 → UTC is already June 14
        fake_now = datetime(2026, 6, 14, 2, 15, 0, tzinfo=ZoneInfo("UTC"))
        expected_date = "13/06/2026"  # Peru date, not UTC date ("14/06/2026")

        captured = {}

        def fake_append_row(sh, tab, row):
            captured["tab"] = tab
            captured["row"] = row

        with patch("handler.datetime") as mock_dt, \
             patch("handler.get_sheet", return_value=MagicMock()), \
             patch("handler.append_row", side_effect=fake_append_row):

            mock_dt.now.return_value = fake_now.astimezone(ZoneInfo("America/Lima"))

            handler._handle_registro(_make_result(scope="pareja"))

        assert captured["tab"] == "Pareja"
        assert captured["row"][0] == expected_date, (
            f"Expected Peru date {expected_date!r}, got {captured['row'][0]!r}. "
            "Lambda is writing UTC date instead of Peru date."
        )

    def test_cristian_gasto_writes_peru_date_after_7pm(self):
        fake_now = datetime(2026, 6, 14, 2, 15, 0, tzinfo=ZoneInfo("UTC"))
        expected_date = "13/06/2026"

        captured = {}

        def fake_append_row(sh, tab, row):
            captured["tab"] = tab
            captured["row"] = row

        with patch("handler.datetime") as mock_dt, \
             patch("handler.get_sheet", return_value=MagicMock()), \
             patch("handler.append_row", side_effect=fake_append_row):

            mock_dt.now.return_value = fake_now.astimezone(ZoneInfo("America/Lima"))

            handler._handle_registro(_make_result(scope="cristian"))

        assert captured["row"][0] == expected_date

    def test_date_before_7pm_matches_both_utc_and_peru(self):
        # At 3pm Peru → UTC is still the same day, both should agree
        fake_now_peru = datetime(2026, 6, 13, 15, 0, 0, tzinfo=ZoneInfo("America/Lima"))
        expected_date = "13/06/2026"

        captured = {}

        def fake_append_row(sh, tab, row):
            captured["row"] = row

        with patch("handler.datetime") as mock_dt, \
             patch("handler.get_sheet", return_value=MagicMock()), \
             patch("handler.append_row", side_effect=fake_append_row):

            mock_dt.now.return_value = fake_now_peru

            handler._handle_registro(_make_result(scope="pareja"))

        assert captured["row"][0] == expected_date

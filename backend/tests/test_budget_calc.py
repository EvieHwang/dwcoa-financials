"""Tests for budget calculation service."""

import pytest
from datetime import date

from app.services.budget_calc import calculate_ytd_budget


class TestCalculateYtdBudget:
    """Tests for YTD budget calculation."""

    def test_monthly_timing_full_year(self):
        """Monthly timing should prorate by month."""
        annual = 1200.0
        # December (month 12) = full year
        result = calculate_ytd_budget(annual, 'monthly', date(2025, 12, 15))
        assert result == 1200.0

    def test_monthly_timing_half_year(self):
        """Monthly timing at 6 months = half budget."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'monthly', date(2025, 6, 15))
        assert result == 600.0

    def test_monthly_timing_january(self):
        """Monthly timing at January = 1/12 of budget."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'monthly', date(2025, 1, 15))
        assert result == 100.0

    def test_quarterly_timing_q1(self):
        """Quarterly timing in Q1 = 1/4 (1 quarter through)."""
        annual = 1200.0
        # March is Q1, 1 quarter through
        result = calculate_ytd_budget(annual, 'quarterly', date(2025, 3, 15))
        assert result == 300.0

    def test_quarterly_timing_q2(self):
        """Quarterly timing in Q2 = 2/4 (2 quarters through)."""
        annual = 1200.0
        # April is Q2, 2 quarters through
        result = calculate_ytd_budget(annual, 'quarterly', date(2025, 4, 15))
        assert result == 600.0

    def test_quarterly_timing_q3(self):
        """Quarterly timing in Q3 = 3/4 (3 quarters through)."""
        annual = 1200.0
        # August is Q3, 3 quarters through
        result = calculate_ytd_budget(annual, 'quarterly', date(2025, 8, 15))
        assert result == 900.0

    def test_quarterly_timing_q4(self):
        """Quarterly timing in Q4 = 4/4 (4 quarters through)."""
        annual = 1200.0
        # October is Q4, 4 quarters through
        result = calculate_ytd_budget(annual, 'quarterly', date(2025, 10, 15))
        assert result == 1200.0

    def test_quarterly_timing_end_of_year(self):
        """Quarterly timing in December = 4/4 (full year)."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'quarterly', date(2025, 12, 15))
        assert result == 1200.0

    def test_annual_timing_january(self):
        """Annual timing should return full amount regardless of month."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'annual', date(2025, 1, 1))
        assert result == 1200.0

    def test_annual_timing_june(self):
        """Annual timing mid-year still returns full amount."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'annual', date(2025, 6, 15))
        assert result == 1200.0

    def test_annual_timing_december(self):
        """Annual timing at year end returns full amount."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'annual', date(2025, 12, 31))
        assert result == 1200.0

    def test_unknown_timing_defaults_to_annual(self):
        """Unknown timing pattern defaults to annual."""
        annual = 1200.0
        result = calculate_ytd_budget(annual, 'unknown', date(2025, 6, 15))
        assert result == 1200.0

    def test_zero_budget(self):
        """Zero budget should return zero."""
        result = calculate_ytd_budget(0.0, 'monthly', date(2025, 6, 15))
        assert result == 0.0


class TestBudgetScenarios:
    """Real-world budget scenarios from spec."""

    def test_fire_alarm_monthly_august(self):
        """Fire Alarm (monthly $3,300) in August = $2,200."""
        annual = 3300.0
        result = calculate_ytd_budget(annual, 'monthly', date(2025, 8, 15))
        assert result == pytest.approx(2200.0, rel=0.01)

    def test_cintas_quarterly_august(self):
        """Cintas Fire Protection (quarterly $1,500) in August = $1,125.

        August is Q3, so 3 quarters through = $1,125.
        """
        annual = 1500.0
        result = calculate_ytd_budget(annual, 'quarterly', date(2025, 8, 15))
        assert result == pytest.approx(1125.0, rel=0.01)

    def test_bulger_annual_august(self):
        """Bulger Safe & Lock (annual $400) in August = $400."""
        annual = 400.0
        result = calculate_ytd_budget(annual, 'annual', date(2025, 8, 15))
        assert result == 400.0

    def test_dues_monthly_may(self):
        """Unit dues (monthly) in May = 5/12 of annual."""
        annual = 5954.75
        result = calculate_ytd_budget(annual, 'monthly', date(2025, 5, 15))
        expected = (5954.75 / 12) * 5
        assert result == pytest.approx(expected, rel=0.01)

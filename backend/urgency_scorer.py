"""
urgency_scorer.py — AlloCare Urgency Scoring Algorithm
Formula: score = (severity × log(frequency + 1)) / max(1, days_since_first_report)
Normalized to 0-100. Transparent formula shown on dashboard.
"""
import math
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def calculate_urgency_score(severity: int, frequency: int, days_since_first_report: int) -> dict:
    """
    Calculates urgency score using the AlloCare formula.

    Args:
        severity: 1-10 from Gemini extraction
        frequency: count of same issue_type × zone in last 30 days
        days_since_first_report: staleness penalty

    Returns:
        dict with keys: score (int 0-100), label (str), color (str), formula_display (str)
    """
    # Clamp inputs
    severity = max(1, min(10, int(severity)))
    frequency = max(0, int(frequency))
    days = max(1, int(days_since_first_report))

    # Core formula
    raw = (severity * math.log(frequency + 1)) / days
    normalized = min(100, round(raw * 10))

    # Thresholds
    if normalized >= 86:
        label = "critical"
        color = "#E02424"
        badge = "CRITICAL"
    elif normalized >= 61:
        label = "high"
        color = "#F97316"
        badge = "HIGH"
    elif normalized >= 31:
        label = "medium"
        color = "#E3A008"
        badge = "MEDIUM"
    else:
        label = "low"
        color = "#0E9F6E"
        badge = "LOW"

    formula_display = (
        f"Score = ({severity} × log({frequency}+1)) / {days} = {raw:.2f} → {normalized}/100"
    )

    return {
        "score": normalized,
        "label": label,
        "color": color,
        "badge": badge,
        "formula_display": formula_display,
        "inputs": {
            "severity": severity,
            "frequency": frequency,
            "days_since_first_report": days,
        }
    }


def recalculate_all_scores(db) -> int:
    """
    Recalculates urgency scores for all open need reports.
    Used after bulk CSV import. Returns count of updated docs.
    """
    updated = 0
    reports = db.collection("need_reports").where("status", "==", "open").stream()

    for report in reports:
        data = report.to_dict()
        try:
            score_data = calculate_urgency_score(
                severity=data.get("severity_score", 5),
                frequency=data.get("report_frequency_30d", 1),
                days_since_first_report=max(1, (
                    datetime.now(timezone.utc) - data.get("created_at", datetime.now(timezone.utc))
                ).days)
            )
            db.collection("need_reports").document(report.id).update({
                "urgency_score": score_data["score"],
                "urgency_label": score_data["label"],
            })
            updated += 1
        except Exception as e:
            logger.warning(f"[recalculate_all_scores] Skipping {report.id}: {e}")

    return updated


def detect_trend(db, zone: str, issue_type: str, lookback_days: int = 30) -> tuple[str, str]:
    """
    Detects trend direction for a zone/issue_type pair using linear regression
    over 4 weekly buckets.

    Returns: (trend_direction, trend_label)
    trend_direction: 'rising' | 'stable' | 'falling'
    """
    now = datetime.now(timezone.utc)
    weeks = []

    for week_start_days, week_end_days in [(22, 30), (15, 21), (8, 14), (1, 7)]:
        start = now - timedelta(days=week_end_days)
        end = now - timedelta(days=week_start_days)
        try:
            count_result = (
                db.collection("need_reports")
                .where("zone", "==", zone)
                .where("issue_type", "==", issue_type)
                .where("created_at", ">=", start)
                .where("created_at", "<", end)
                .count()
                .get()
            )
            count = count_result[0][0].value if count_result else 0
        except Exception:
            count = 0
        weeks.append(count)

    # Simple linear regression slope
    n = len(weeks)
    if n < 2:
        return "stable", "→ Trend: Stable"

    x_mean = (n - 1) / 2
    y_mean = sum(weeks) / n
    numerator = sum((i - x_mean) * (weeks[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0

    if slope > 0.5:
        return "rising", "⬆ Trend: Increasing urgency"
    elif slope < -0.5:
        return "falling", "⬇ Trend: Improving situation"
    else:
        return "stable", "→ Trend: Stable"

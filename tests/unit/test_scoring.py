from app.models.enums import IOCType
from app.services.scoring_service import ScoringService


def test_high_reliability_watchlisted_ransomware_has_priority_above_nine() -> None:
    result = ScoringService.calculate(
        source_reliability=1.0,
        observation_count=10,
        days_since_last_seen=0,
        is_watchlisted=True,
        tags={"ransomware"},
        has_enrichment=True,
        ioc_type=IOCType.SHA256,
    )
    assert result.priority > 9.0


def test_false_positive_tag_drops_confidence_below_ten() -> None:
    result = ScoringService.calculate(
        source_reliability=0.4,
        observation_count=1,
        days_since_last_seen=5,
        is_watchlisted=False,
        tags={"false-positive"},
        has_enrichment=False,
        ioc_type=IOCType.DOMAIN,
    )
    assert result.confidence < 10.0


def test_recency_decay_applies_after_30_days() -> None:
    recent = ScoringService.calculate(
        source_reliability=0.8,
        observation_count=2,
        days_since_last_seen=1,
        is_watchlisted=False,
        tags=set(),
        has_enrichment=False,
        ioc_type=IOCType.IPV4,
    )
    stale = ScoringService.calculate(
        source_reliability=0.8,
        observation_count=2,
        days_since_last_seen=30,
        is_watchlisted=False,
        tags=set(),
        has_enrichment=False,
        ioc_type=IOCType.IPV4,
    )
    assert stale.confidence < recent.confidence


def test_confidence_is_always_bounded_between_zero_and_hundred() -> None:
    low = ScoringService.calculate(
        source_reliability=0.0,
        observation_count=0,
        days_since_last_seen=999,
        is_watchlisted=False,
        tags={"false-positive"},
        has_enrichment=False,
        ioc_type=IOCType.DOMAIN,
    )
    high = ScoringService.calculate(
        source_reliability=10.0,
        observation_count=10_000,
        days_since_last_seen=0,
        is_watchlisted=True,
        tags={"ransomware", "malware"},
        has_enrichment=True,
        ioc_type=IOCType.SHA256,
    )
    assert 0.0 <= low.confidence <= 100.0
    assert 0.0 <= high.confidence <= 100.0

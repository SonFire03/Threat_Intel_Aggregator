from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import IOCType

_MALICIOUS_TAGS = {"malware", "c2", "ransomware", "phishing"}
_SEVERITY_BY_TAG = {
    "ransomware": 10.0,
    "c2": 9.0,
    "malware": 8.0,
    "phishing": 7.0,
    "cryptomining": 6.0,
    "tor-exit": 5.0,
    "scanner": 4.0,
}
_HASH_TYPES = {IOCType.MD5, IOCType.SHA1, IOCType.SHA256}


@dataclass(frozen=True)
class ScoreResult:
    confidence: float
    severity: float
    priority: float


class ScoringService:
    @staticmethod
    def calculate(
        *,
        source_reliability: float,
        observation_count: int,
        days_since_last_seen: int,
        is_watchlisted: bool,
        tags: set[str],
        has_enrichment: bool,
        ioc_type: IOCType,
    ) -> ScoreResult:
        normalized_tags = {tag.lower() for tag in tags}

        confidence = (
            source_reliability * 30.0
            + min(observation_count / 5.0 * 20.0, 20.0)
            + max(0.0, 20.0 - float(days_since_last_seen))
            + (15.0 if is_watchlisted else 0.0)
            + (10.0 if normalized_tags & _MALICIOUS_TAGS else 0.0)
            + (5.0 if has_enrichment else 0.0)
            + (-40.0 if "false-positive" in normalized_tags else 0.0)
        )
        bounded_confidence = max(0.0, min(100.0, confidence))

        severity = ScoringService._severity_for(ioc_type=ioc_type, tags=normalized_tags)
        priority = (bounded_confidence / 100.0) * severity
        return ScoreResult(confidence=bounded_confidence, severity=severity, priority=priority)

    @staticmethod
    def _severity_for(*, ioc_type: IOCType, tags: set[str]) -> float:
        severity_from_tag = max(
            (_SEVERITY_BY_TAG[tag] for tag in tags if tag in _SEVERITY_BY_TAG),
            default=0.0,
        )
        if severity_from_tag > 0:
            return severity_from_tag
        if ioc_type in _HASH_TYPES:
            return 7.0
        if ioc_type is IOCType.URL:
            return 6.0
        return 5.0

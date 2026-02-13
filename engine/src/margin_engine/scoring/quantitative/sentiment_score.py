"""Sentiment Score factor.

Accepts a pre-computed sentiment value produced by LLM analysis of
news, earnings calls, and analyst reports. The actual LLM call lives
in the qualitative/ingestion layer; this factor only handles
normalization and the contrarian-bonus adjustment.

Scoring pipeline:
    1. The ingestion layer runs LLM analysis (temperature=0, deterministic)
       with source weights: earnings calls > analyst reports > news.
    2. The result is a single score in the [-5, +5] range.
    3. This factor normalizes to a 0-10 scale and optionally applies a
       contrarian bonus (+2.0) when strong fundamentals coincide with
       negative sentiment.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_MIN_SCORE = -5.0
_MAX_SCORE = 5.0
_CONTRARIAN_BONUS = 2.0
_MAX_NORMALIZED = 10.0


def sentiment_score(
    score: float,
    has_contrarian_signal: bool = False,
) -> FactorScore:
    """Compute the normalized sentiment score with optional contrarian bonus.

    Parameters
    ----------
    score:
        Pre-computed sentiment value from -5.0 to +5.0.  Values outside
        this range are clamped.
    has_contrarian_signal:
        Whether the stock has strong fundamentals despite negative sentiment
        (determined externally by the qualitative pipeline).

    Returns
    -------
    FactorScore with:
        - name: "sentiment"
        - raw_value: normalized score on a 0-10 scale
        - percentile_rank: 0.0 (placeholder for Phase 6 composite scorer)
        - detail: human-readable breakdown
    """
    # 1. Clamp to valid range.
    clamped = max(_MIN_SCORE, min(_MAX_SCORE, score))

    # 2. Normalize to 0-10 scale: -5 -> 0, 0 -> 5, +5 -> 10.
    normalized = clamped + 5.0

    # 3. Apply contrarian bonus if applicable.
    contrarian_applied = False
    if has_contrarian_signal and clamped < 0.0:
        normalized = min(normalized + _CONTRARIAN_BONUS, _MAX_NORMALIZED)
        contrarian_applied = True

    # 4. Build detail string.
    detail = (
        f"score={score:.1f}"
        f" -> clamped={clamped:.1f}"
        f" -> normalized={normalized:.1f}"
    )
    if contrarian_applied:
        detail += f" (includes contrarian bonus of +{_CONTRARIAN_BONUS:.1f})"

    return FactorScore(
        name="sentiment",
        raw_value=normalized,
        percentile_rank=0.0,
        detail=detail,
    )

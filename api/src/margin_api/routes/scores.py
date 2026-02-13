"""Score endpoints for the Margin Invest API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from margin_api.schemas.scores import ScoreListResponse, ScoreResponse

router = APIRouter(prefix="/api/v1/scores", tags=["scores"])

# In-memory score store (replaced by DB in later phase)
_score_store: dict[str, ScoreResponse] = {}


@router.post("/{ticker}", response_model=ScoreResponse, status_code=201)
async def create_score(ticker: str, score: ScoreResponse) -> ScoreResponse:
    """Store a scoring result for a ticker.

    In production, this will trigger the scoring engine. For now, accepts
    a pre-computed score and stores it.
    """
    ticker = ticker.upper()
    if score.ticker.upper() != ticker:
        raise HTTPException(
            status_code=400,
            detail=f"Ticker mismatch: URL has {ticker}, body has {score.ticker}",
        )
    # Normalize ticker to uppercase on the stored object
    normalized = score.model_copy(update={"ticker": ticker})
    _score_store[ticker] = normalized
    return normalized


@router.get("", response_model=ScoreListResponse)
async def list_scores(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    min_percentile: float = Query(0.0, ge=0.0, le=100.0),
    conviction: str | None = Query(None),
) -> ScoreListResponse:
    """List all scored assets, with optional filtering and pagination."""
    scores = list(_score_store.values())

    # Filter by minimum percentile
    if min_percentile > 0:
        scores = [s for s in scores if s.composite_percentile >= min_percentile]

    # Filter by conviction level
    if conviction:
        scores = [s for s in scores if s.conviction_level == conviction.lower()]

    # Sort by composite percentile descending
    scores.sort(key=lambda s: s.composite_percentile, reverse=True)

    total = len(scores)
    start = (page - 1) * page_size
    end = start + page_size
    page_scores = scores[start:end]

    return ScoreListResponse(
        scores=page_scores,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticker}", response_model=ScoreResponse)
async def get_score(ticker: str) -> ScoreResponse:
    """Get the scoring result for a specific ticker."""
    ticker = ticker.upper()
    if ticker not in _score_store:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")
    return _score_store[ticker]


@router.delete("/{ticker}", status_code=204)
async def delete_score(ticker: str) -> None:
    """Remove a score from the store."""
    ticker = ticker.upper()
    if ticker not in _score_store:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")
    del _score_store[ticker]

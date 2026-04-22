"""Claude-powered material change classifier for risk factor diffs.

Sends pre-filtered change candidates to Claude Haiku 4.5 with prompt caching,
parses structured JSON output, and logs every call to the llm_call_log table.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING

import anthropic

from margin_api.services.risk_diffing.config import get_analysis_model, get_prompt_version

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from margin_api.services.risk_diffing.diff_engine import ChangeCandidate

logger = logging.getLogger(__name__)
_client: anthropic.AsyncAnthropic | None = None

_INPUT_COST_PER_TOKEN = 1.0 / 1_000_000
_OUTPUT_COST_PER_TOKEN = 5.0 / 1_000_000

SYSTEM_PROMPT = """\
You are a financial analyst specializing in SEC 10-K risk factor analysis.

You will receive a list of changes detected between a company's current and prior year \
Item 1A Risk Factors section. For each change, classify it and assess its severity.

## Output Schema

Return ONLY valid JSON matching this structure:
{
  "material_changes": [
    {
      "change_type": "new" | "removed" | "expanded" | "softened",
      "topic": "short topic label (3-8 words)",
      "severity": 1-10,
      "summary_50_words": "concise summary of the change and its implications",
      "verbatim_new_text": "exact text from current filing (or null if removed)",
      "verbatim_old_text": "exact text from prior filing (or null if new)"
    }
  ],
  "overall_risk_delta_score": -10.0 to +10.0,
  "model_confidence": 0.0 to 1.0
}

## Change Type Classification

- "new": Risk factor not present in prior year. Use verbatim_old_text: null.
- "removed": Risk factor present in prior year but absent now. Use verbatim_new_text: null.
- "expanded": Risk factor existed before but has been materially expanded with new detail.
- "softened": Risk factor existed before but language has been softened or scope reduced.

For inputs labeled MODIFIED, you must classify as either "expanded" or "softened".

## Severity Calibration

1-3: Routine language updates. Regulatory boilerplate changes. Minor wording adjustments.
4-6: Meaningful new disclosures. New market risk, litigation mention, customer concentration.
7-8: Material risks with potential financial impact. Covenant violations, going concern, \
regulatory investigations, significant write-downs.
9-10: Existential risks. Fraud disclosure, imminent insolvency, SEC enforcement action, \
restatement of financials.

## Examples

Example 1 (severity 3):
Old: "We face competition from established companies."
New: "We face competition from established companies and new market entrants."
Classification: expanded, severity 3.

Example 2 (severity 9):
Old: (none)
New: "We are subject to an ongoing SEC investigation regarding our revenue recognition."
Classification: new, severity 9.

Example 3 (severity 6):
Old: "We may be unable to attract and retain key employees."
New: "We have experienced significant turnover in senior management, including the departure \
of our CFO and two division presidents in the past year."
Classification: expanded, severity 6.

## overall_risk_delta_score

Positive = risk profile deteriorated. Negative = risk profile improved. Zero = neutral.

## model_confidence

Your confidence in the classifications (0.0-1.0). Lower if text is ambiguous or boilerplate-heavy.\
"""


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


def build_user_prompt(ticker: str, candidates: list[ChangeCandidate]) -> str:
    """Build the user prompt from change candidates."""
    parts = [f"Ticker: {ticker}\n\nAnalyze the following changes:\n"]
    for i, c in enumerate(candidates, 1):
        if c.change_type == "new":
            parts.append(f"--- CHANGE {i}: NEW RISK FACTOR ---")
            parts.append(f"Current year text:\n{c.new_text}\n")
        elif c.change_type == "removed":
            parts.append(f"--- CHANGE {i}: REMOVED RISK FACTOR ---")
            parts.append(f"Prior year text:\n{c.old_text}\n")
        elif c.change_type == "modified":
            parts.append(
                f"--- CHANGE {i}: MODIFIED RISK FACTOR (similarity: {c.similarity:.2f}) ---"
            )
            parts.append(f"Prior year text:\n{c.old_text}\n")
            parts.append(f"Current year text:\n{c.new_text}\n")
    return "\n".join(parts)


async def analyze_material_changes(
    session: AsyncSession,
    ticker: str,
    candidates: list[ChangeCandidate],
) -> dict | None:
    """Call Claude to classify material changes. Returns structured JSON dict or None."""
    if not candidates:
        return None
    model = get_analysis_model()
    prompt_version = get_prompt_version()
    user_prompt = build_user_prompt(ticker, candidates)
    input_hash = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()
    client = _get_client()
    start_ms = time.monotonic_ns() // 1_000_000
    error_text = None
    result_json = None
    input_tokens = 0
    output_tokens = 0
    try:
        message = await client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.0,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        if not message.content:
            error_text = "Empty response from API"
            logger.warning("[risk_analyzer] %s for %s", error_text, ticker)
            return None
        raw_text = message.content[0].text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
        result_json = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        error_text = f"JSON parse error: {exc}"
        logger.warning("[risk_analyzer] %s for %s", error_text, ticker)
    except Exception as exc:
        error_text = f"API error: {exc}"
        logger.exception("[risk_analyzer] API call failed for %s", ticker)
    latency_ms = (time.monotonic_ns() // 1_000_000) - start_ms
    cost_usd = (input_tokens * _INPUT_COST_PER_TOKEN) + (output_tokens * _OUTPUT_COST_PER_TOKEN)
    await _log_call(
        session=session,
        ticker=ticker,
        model=model,
        prompt_version=prompt_version,
        input_hash=input_hash,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        response_json=result_json,
        error=error_text,
    )
    if result_json is not None:
        result_json["analysis_tokens_used"] = input_tokens + output_tokens
        result_json["analysis_cost_usd"] = cost_usd
    return result_json


async def _log_call(
    session: AsyncSession,
    ticker: str,
    model: str,
    prompt_version: str,
    input_hash: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    response_json: dict | None,
    error: str | None,
) -> None:
    """Write a row to the llm_call_log table."""
    from margin_api.db.models import LLMCallLog

    try:
        row = LLMCallLog(
            service="risk_diffing",
            ticker=ticker,
            model=model,
            prompt_version=prompt_version,
            input_hash=input_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            response_json=response_json,
            error=error,
        )
        session.add(row)
        await session.commit()
    except Exception:
        logger.exception("[risk_analyzer] Failed to log LLM call for %s", ticker)
        await session.rollback()

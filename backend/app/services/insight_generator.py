"""
Insight Generator — Transform raw statistical results into human-readable insights.
Uses LLM to generate contextual interpretations.
"""
import logging
from typing import Any, Dict

from app.services import llm_client

logger = logging.getLogger(__name__)

INSIGHT_PROMPT = """You are a statistics professor explaining results to a student who has NO statistics background.

Given the following statistical analysis results, generate a clear, insightful interpretation.

Analysis type: {method}
Description: {description}

Raw results (JSON):
{results_json}

Write your response in this JSON format:
{{
    "headline": "<one-sentence key finding>",
    "interpretation": "<2-3 paragraph interpretation in plain language>",
    "significance": "<whether results are statistically significant and what that means practically>",
    "recommendations": ["<actionable next steps based on findings>"]
}}

Rules:
- Do NOT just repeat the numbers. EXPLAIN what they mean.
- Use analogies and real-world context when helpful.
- If p < 0.05, explain significance in practical terms.
- If p >= 0.05, explain what "not significant" means (not the same as "no effect").
- Be concise but thorough.
- If the user's language appears to be Vietnamese, respond in Vietnamese.
- Respond ONLY with valid JSON."""


async def generate_insight(
    method: str,
    description: str,
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate human-readable insight from statistical results.
    Returns structured insight with headline, interpretation, significance.
    """
    import json

    results_str = json.dumps(results, indent=2, default=str, ensure_ascii=False)
    # Truncate if too long
    if len(results_str) > 3000:
        results_str = results_str[:3000] + "\n... (truncated)"

    prompt = INSIGHT_PROMPT.format(
        method=method,
        description=description,
        results_json=results_str,
    )

    try:
        insight = await llm_client.chat_json(
            messages=[
                {"role": "system", "content": "You are a statistics professor. Always respond in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        logger.info(f"[PIPELINE] Insight generated via LLM: headline='{insight.get('headline', '')[:80]}'")
        return insight
    except Exception as e:
        logger.warning(f"[PIPELINE] Insight gen FAILED: {e} → using rule-based fallback")
        return _fallback_insight(method, results)


def _fallback_insight(method: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based fallback when LLM is unavailable."""
    headline = f"Analysis complete: {method}"
    interpretation = ""
    significance = ""

    # Extract common fields
    p_value = results.get("pvalue") or results.get("p_value")
    r2 = results.get("r2")
    f_stat = results.get("f_statistic") or results.get("f_stat")

    if p_value is not None:
        if p_value < 0.001:
            significance = f"Highly significant (p < 0.001). Very strong evidence against the null hypothesis."
        elif p_value < 0.01:
            significance = f"Significant (p = {p_value}). Strong evidence against the null hypothesis."
        elif p_value < 0.05:
            significance = f"Significant (p = {p_value}). Evidence suggests a real effect exists."
        else:
            significance = f"Not statistically significant (p = {p_value}). Insufficient evidence to conclude a difference or effect exists."

    if r2 is not None:
        pct = round(r2 * 100, 1)
        interpretation = f"The model explains {pct}% of the variance in the dependent variable."
        if pct > 70:
            interpretation += " This is a strong fit."
        elif pct > 40:
            interpretation += " This is a moderate fit."
        else:
            interpretation += " This is a weak fit — other factors may be important."

    if method == "independent_ttest":
        cohen_d = results.get("cohen_d", 0)
        if abs(cohen_d) < 0.2:
            interpretation = "The effect size is small (Cohen's d < 0.2), suggesting a negligible practical difference."
        elif abs(cohen_d) < 0.5:
            interpretation = "The effect size is small-to-medium, suggesting a noticeable but modest difference."
        elif abs(cohen_d) < 0.8:
            interpretation = "The effect size is medium, suggesting a meaningful practical difference."
        else:
            interpretation = "The effect size is large (Cohen's d > 0.8), suggesting a substantial practical difference."

    return {
        "headline": headline,
        "interpretation": interpretation or "Analysis completed. Review the raw results for details.",
        "significance": significance or "Statistical significance not applicable for this analysis.",
        "recommendations": ["Review the detailed results below for more information."],
    }

"""
Report Generator — Structured statistical report via LLM.
Generates Introduction → Methodology → Results → Discussion.
"""
import logging
from typing import Any, Dict, List

from app.services import llm_client

logger = logging.getLogger(__name__)

REPORT_PROMPT = """You are an academic research assistant generating a statistical analysis report.

Dataset information:
{schema_summary}

Analyses performed:
{analyses_summary}

Generate a complete research report in this JSON format:
{{
    "title": "<descriptive report title>",
    "sections": [
        {{
            "heading": "1. Introduction",
            "content": "<introduction paragraph describing the dataset and analysis objectives>"
        }},
        {{
            "heading": "2. Methodology",
            "content": "<methodology section listing the statistical methods used and why>"
        }},
        {{
            "heading": "3. Results",
            "content": "<results section with key findings, statistics cited>"
        }},
        {{
            "heading": "4. Discussion",
            "content": "<discussion interpreting the findings, limitations, and implications>"
        }},
        {{
            "heading": "5. Conclusion",
            "content": "<brief conclusion with main takeaways>"
        }}
    ]
}}

Rules:
- Cite actual statistics (F values, p values, R², etc.) from the results.
- Write in academic style but accessible to non-experts.
- Each section should be 1-3 paragraphs.
- If the analyses are in Vietnamese context, write in Vietnamese.
- Respond ONLY with valid JSON."""


async def generate_report(
    schema_summary: str,
    analysis_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a structured statistical report from analysis results.
    """
    import json

    # Build analyses summary for prompt
    analyses_parts = []
    for i, result in enumerate(analysis_results, 1):
        method = result.get("method", "unknown")
        description = result.get("description", "")
        insight = result.get("insight", {})
        headline = insight.get("headline", "")
        stats_json = json.dumps(
            {k: v for k, v in result.get("results", {}).items()
             if k in ("statistic", "pvalue", "p_value", "f_statistic", "f_stat",
                       "r2", "adj_r2", "cohen_d", "cohen_dz", "eta_squared",
                       "chi2", "cramers_v", "cronbach_alpha", "kmo")},
            default=str,
        )
        analyses_parts.append(
            f"Analysis {i}: {method} — {description}\n"
            f"  Key finding: {headline}\n"
            f"  Statistics: {stats_json}"
        )

    analyses_str = "\n\n".join(analyses_parts) if analyses_parts else "No analyses performed."

    prompt = REPORT_PROMPT.format(
        schema_summary=schema_summary,
        analyses_summary=analyses_str,
    )

    try:
        report = await llm_client.chat_json(
            messages=[
                {"role": "system", "content": "You are an academic research assistant. Always respond in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=3000,
        )
        return report
    except Exception as e:
        logger.warning(f"Report generation failed: {e}")
        return _fallback_report(schema_summary, analysis_results)


def _fallback_report(schema_summary: str, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a simple report when LLM is unavailable."""
    methods = [r.get("method", "unknown") for r in analysis_results]
    headlines = [r.get("insight", {}).get("headline", "") for r in analysis_results]

    return {
        "title": "Statistical Analysis Report",
        "sections": [
            {
                "heading": "1. Introduction",
                "content": f"This report presents the results of a statistical analysis. {schema_summary.split(chr(10))[0]}",
            },
            {
                "heading": "2. Methodology",
                "content": f"The following methods were applied: {', '.join(methods)}.",
            },
            {
                "heading": "3. Results",
                "content": "\n".join(f"- {h}" for h in headlines if h) or "See detailed results above.",
            },
            {
                "heading": "4. Discussion",
                "content": "The results should be interpreted in the context of the study design and limitations.",
            },
            {
                "heading": "5. Conclusion",
                "content": f"A total of {len(analysis_results)} analyses were conducted. Refer to individual results for detailed findings.",
            },
        ],
    }

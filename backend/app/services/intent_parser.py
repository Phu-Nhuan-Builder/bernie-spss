"""
Intent Parser — NL query → structured statistical intent.
Hybrid approach: LLM for understanding, rule-based for correctness.

CRITICAL FIX: Uses fuzzy variable matching in validation to prevent
silent nullification of LLM's variable choices.
"""
import logging
from difflib import get_close_matches
from typing import Any, Dict, List, Optional

from app.services import llm_client

logger = logging.getLogger(__name__)

# ── Supported intents and their descriptions ──────────────────────────────────
SUPPORTED_INTENTS = {
    "compare_groups": "Compare means between 2+ groups (t-test, ANOVA)",
    "find_relationship": "Find relationship/correlation between variables",
    "predict": "Predict a dependent variable from independent variables (regression)",
    "describe": "Descriptive statistics, frequencies, summaries",
    "test_normality": "Test if data follows a normal distribution",
    "crosstab": "Cross-tabulation with chi-square for categorical variables",
    "reliability": "Reliability analysis (Cronbach's alpha)",
    "factor_analysis": "Exploratory factor analysis",
}

INTENT_PARSE_PROMPT = """You are a statistical methods expert. Given a user's natural language query about data analysis, determine the statistical intent.

Available intents:
{intents_desc}

Dataset context:
{schema_summary}

EXACT column names in this dataset (YOU MUST USE THESE EXACT NAMES):
{column_list}

User query: "{query}"

Respond in JSON with this exact format:
{{
    "intent": "<one of the intent keys above>",
    "confidence": <0.0 to 1.0>,
    "variables": {{
        "dependent": "<EXACT column name from list above, or null>",
        "independent": ["<EXACT column names from list above>"],
        "group_var": "<EXACT column name from list above, or null>"
    }},
    "filter_values": {{
        "<column_name>": ["value1", "value2"]
    }},
    "reasoning": "<brief explanation of why this intent was chosen>"
}}

Rules:
- You MUST use EXACT column names from the list above. Do NOT invent column names.
- If the user mentions a concept (e.g. "GDP"), find the closest matching column name (e.g. "GDP per capita").
- If the user mentions specific variables, map them to the closest column names.
- If the user mentions specific entities to compare (e.g. "Vietnam and China"), extract them in filter_values with the grouping column as key.
- filter_values is for filtering rows. Example: user says "compare Vietnam and China" → filter_values: {{"Country or region": ["Vietnam", "China"]}}
- If the user wants ALL groups compared, set filter_values to {{}}.
- If the user is vague, suggest the most likely variables based on the dataset.
- For compare_groups: set group_var to a categorical column, dependent to a numeric column.
- For find_relationship: put all relevant numeric columns in "independent".
- For predict: set dependent to the target, independent to predictors.
- If unsure, set confidence below 0.5.
- Respond ONLY with valid JSON, no extra text."""


async def parse_intent(
    query: str,
    schema_summary: str,
    variable_names: List[str],
) -> Dict[str, Any]:
    """
    Parse a natural language query into a structured intent.
    Uses LLM for understanding, then validates with rules.
    """
    # Build intents description
    intents_desc = "\n".join(f"- {k}: {v}" for k, v in SUPPORTED_INTENTS.items())

    # Build explicit column list for LLM
    column_list = ", ".join(f'"{v}"' for v in variable_names)

    prompt = INTENT_PARSE_PROMPT.format(
        intents_desc=intents_desc,
        schema_summary=schema_summary,
        column_list=column_list,
        query=query,
    )

    try:
        result = await llm_client.chat_json(
            messages=[
                {"role": "system", "content": "You are a statistical analysis expert. Always respond in valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        result["_source"] = "llm"
        logger.info(f"[PIPELINE] Intent parsed via LLM: intent={result.get('intent')}, confidence={result.get('confidence')}, vars={result.get('variables')}")
    except Exception as e:
        logger.warning(f"[PIPELINE] LLM intent parsing FAILED: {e} → falling back to rule-based")
        result = _rule_based_fallback(query, variable_names)
        result["_source"] = "rule_fallback"
        logger.info(f"[PIPELINE] Intent parsed via FALLBACK: intent={result.get('intent')}")

    # Validate and normalize (with fuzzy matching instead of nullification)
    result = _validate_intent(result, variable_names)
    return result


def _rule_based_fallback(query: str, variable_names: List[str]) -> Dict[str, Any]:
    """Simple keyword-based intent detection as fallback."""
    q = query.lower()

    if any(w in q for w in ["compare", "difference", "so sánh", "khác biệt", "t-test", "anova"]):
        return {"intent": "compare_groups", "confidence": 0.6, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: comparison"}

    if any(w in q for w in ["relationship", "correlation", "tương quan", "liên hệ", "mối quan hệ"]):
        return {"intent": "find_relationship", "confidence": 0.6, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: relationship"}

    if any(w in q for w in ["predict", "regression", "affect", "influence", "hồi quy", "ảnh hưởng", "tác động"]):
        return {"intent": "predict", "confidence": 0.6, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: prediction"}

    if any(w in q for w in ["normal", "normality", "phân phối chuẩn", "shapiro"]):
        return {"intent": "test_normality", "confidence": 0.7, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: normality"}

    if any(w in q for w in ["crosstab", "chi-square", "bảng chéo"]):
        return {"intent": "crosstab", "confidence": 0.7, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: crosstab"}

    if any(w in q for w in ["reliability", "cronbach", "độ tin cậy"]):
        return {"intent": "reliability", "confidence": 0.7, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: reliability"}

    if any(w in q for w in ["factor", "efa", "nhân tố"]):
        return {"intent": "factor_analysis", "confidence": 0.7, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "Keyword match: factor analysis"}

    # Default: describe
    return {"intent": "describe", "confidence": 0.4, "variables": {"dependent": None, "independent": [], "group_var": None}, "reasoning": "No clear intent, defaulting to descriptives"}


def _fuzzy_match_var(name: str, variable_names: List[str], cutoff: float = 0.5) -> Optional[str]:
    """
    Try to match a variable name against the dataset columns.
    Order: exact → case-insensitive → substring → fuzzy (difflib).
    """
    if not name:
        return None

    # 1. Exact match
    if name in variable_names:
        return name

    # 2. Case-insensitive exact match
    lower_map = {v.lower(): v for v in variable_names}
    if name.lower() in lower_map:
        return lower_map[name.lower()]

    # 3. Substring match (MORE RELIABLE than fuzzy — check first)
    for v in variable_names:
        if name.lower() in v.lower() or v.lower() in name.lower():
            logger.info(f"[PIPELINE] Substring matched variable: '{name}' → '{v}'")
            return v

    # 4. Fuzzy match (last resort — difflib can produce false positives)
    matches = get_close_matches(name.lower(), [v.lower() for v in variable_names], n=1, cutoff=cutoff)
    if matches:
        matched = lower_map[matches[0]]
        logger.info(f"[PIPELINE] Fuzzy matched variable: '{name}' → '{matched}'")
        return matched

    return None


def _validate_intent(result: Dict[str, Any], variable_names: List[str]) -> Dict[str, Any]:
    """
    Validate and normalize the parsed intent.
    Uses fuzzy matching instead of silently nullifying variables.
    """
    # Ensure required fields
    if "intent" not in result or result["intent"] not in SUPPORTED_INTENTS:
        result["intent"] = "describe"
        result["confidence"] = 0.3

    if "confidence" not in result:
        result["confidence"] = 0.5

    if "variables" not in result:
        result["variables"] = {"dependent": None, "independent": [], "group_var": None}

    # Validate variable names with FUZZY MATCHING (not silent nullification)
    vars_section = result["variables"]

    # Normalize types — LLM sometimes returns unexpected shapes
    dep = vars_section.get("dependent")
    indep = vars_section.get("independent")
    grp = vars_section.get("group_var")

    # dependent could be a list — take first, move rest to independent
    if isinstance(dep, list):
        extras = dep[1:]
        dep = dep[0] if dep else None
        if not isinstance(indep, list):
            indep = []
        indep = extras + indep

    # independent could be None or a string
    if indep is None:
        indep = []
    if isinstance(indep, str):
        indep = [indep]

    # group_var could be a list
    if isinstance(grp, list):
        grp = grp[0] if grp else None

    vars_section["dependent"] = dep
    vars_section["independent"] = indep
    vars_section["group_var"] = grp

    # Dependent variable — fuzzy match
    if vars_section.get("dependent"):
        original = vars_section["dependent"]
        matched = _fuzzy_match_var(original, variable_names)
        if matched:
            vars_section["dependent"] = matched
        else:
            logger.warning(f"[PIPELINE] ⚠ Variable '{original}' NOT found in dataset (even with fuzzy match) → nullified")
            vars_section["dependent"] = None

    # Independent variables — fuzzy match each
    if vars_section.get("independent"):
        original_list = vars_section["independent"]
        matched_list = []
        for v in original_list:
            if not isinstance(v, str):
                continue
            matched = _fuzzy_match_var(v, variable_names)
            if matched:
                matched_list.append(matched)
            else:
                logger.warning(f"[PIPELINE] ⚠ Variable '{v}' NOT found in dataset → dropped from independent list")
        vars_section["independent"] = matched_list

    # Group variable — fuzzy match
    if vars_section.get("group_var"):
        original = vars_section["group_var"]
        matched = _fuzzy_match_var(original, variable_names)
        if matched:
            vars_section["group_var"] = matched
        else:
            logger.warning(f"[PIPELINE] ⚠ Variable '{original}' NOT found in dataset → nullified")
            vars_section["group_var"] = None

    return result

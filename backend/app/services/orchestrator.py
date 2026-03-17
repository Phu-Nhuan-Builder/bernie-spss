"""
Orchestrator — Central coordination layer.
Ties together: schema inference → intent parsing → method routing → stats execution → chart/table building → insight generation.

ARCHITECTURE:
  1. LLM parses user query → structured intent (intent_parser.py)
  2. Rule-based router maps intent → exact method + params (method_router.py)
  3. Stats engine executes real computation (domain/services/*.py)
  4. Chart + Table builders format results (chart_builder.py, table_builder.py)
  5. LLM generates human insight from computed results (insight_generator.py)

DEBUG: All pipeline steps are logged at INFO level for traceability.
"""
import logging
import json
from typing import Any, Dict, List

import pandas as pd

from app.services.schema_inference import infer_schema
from app.services.intent_parser import parse_intent
from app.services.method_router import route_method, plan_auto_analysis
from app.services.insight_generator import generate_insight
from app.services.report_generator import generate_report
from app.services.chart_builder import build_charts
from app.services.table_builder import build_tables

# Import statistical engines
from app.domain.services.descriptives import (
    compute_descriptives, compute_frequencies, compute_crosstabs, compute_explore,
)
from app.domain.services.tests import (
    independent_ttest, paired_ttest, one_sample_ttest, one_way_anova,
)
from app.domain.services.regression import (
    pearson_spearman_correlation, ols_regression, binary_logistic,
)
from app.domain.services.factor_analysis import run_efa, run_reliability
from app.domain.services.spss_io import get_session

logger = logging.getLogger(__name__)


def _log_pipeline(step: str, data: Any, max_len: int = 500) -> None:
    """Debug log for pipeline traceability."""
    try:
        serialized = json.dumps(data, default=str, ensure_ascii=False)
        if len(serialized) > max_len:
            serialized = serialized[:max_len] + "...(truncated)"
        logger.info(f"[PIPELINE] {step}: {serialized}")
    except Exception:
        logger.info(f"[PIPELINE] {step}: <unserializable>")


def _sanitize_results(obj: Any) -> Any:
    """Recursively convert numpy types to native Python for JSON serialization."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _sanitize_results(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_results(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        if not np.isfinite(val):
            return None
        return val
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float):
        if not np.isfinite(obj):
            return None
    return obj


async def analyze(session_id: str, query: str) -> Dict[str, Any]:
    """
    Main NL analysis pipeline:
    query → intent → method → execute → charts + tables → insight → response
    """
    logger.info(f"[PIPELINE] ═══ START analyze(query='{query}') ═══")

    df, meta = get_session(session_id)
    schema = infer_schema(df)
    _log_pipeline("schema_vars", {
        "numeric": schema.get("numeric_vars", []),
        "categorical": schema.get("categorical_vars", []),
        "n_rows": len(df),
    })

    # 1. Parse intent — LLM first, rule-based fallback
    intent = await parse_intent(
        query=query,
        schema_summary=schema["summary_text"],
        variable_names=list(df.columns),
    )
    _log_pipeline("parsed_intent", intent)

    # 1.5 Apply filter_values — filter DataFrame to specific entities
    filter_values = intent.get("filter_values", {})
    if filter_values and isinstance(filter_values, dict):
        for col, values in filter_values.items():
            if not isinstance(values, list) or not values:
                continue
            # Fuzzy match column name
            matched_col = None
            for c in df.columns:
                if col.lower() in c.lower() or c.lower() in col.lower():
                    matched_col = c
                    break
            if not matched_col:
                continue

            # Fuzzy match filter values against actual data values
            actual_values = df[matched_col].dropna().unique().tolist()
            matched_values = []
            for fv in values:
                fv_lower = str(fv).lower()
                for av in actual_values:
                    av_str = str(av).lower()
                    if fv_lower in av_str or av_str in fv_lower:
                        matched_values.append(av)
                        break

            if matched_values:
                before_len = len(df)
                df = df[df[matched_col].isin(matched_values)].copy()
                logger.info(f"[PIPELINE] Filtered '{matched_col}' to {matched_values}: {before_len} → {len(df)} rows")
                # Re-infer schema for filtered data
                schema = infer_schema(df)

    # EDGE CASE: Empty df after filtering
    if len(df) == 0:
        logger.warning("[PIPELINE] ⚠ DataFrame is empty after filtering")
        return {
            "status": "error",
            "message": "No data matches the specified filter. Check if the entities exist in your dataset.",
            "intent": intent,
            "charts": [],
            "tables": [],
        }

    # 2. Route to method — deterministic mapping
    plan = route_method(intent, schema, df)
    _log_pipeline("execution_plan", plan)

    if plan["method"] == "error":
        logger.warning(f"[PIPELINE] Plan resulted in error: {plan['description']}")
        return {
            "status": "error",
            "message": plan["description"],
            "intent": intent,
            "dataset_schema": schema,
            "charts": [],
            "tables": [],
        }

    # 3. Execute real computation — AI-first with graceful degradation
    #    If the AI-selected method fails, try downgrading:
    #    regression → correlation (≥ 3 obs) → descriptives
    n_obs = len(df)
    DEGRADATION_CHAIN = {
        "ols_regression": (
            [("correlation", lambda p: {"variables": [p.get("dependent", "")] + p.get("independents", []), "method": "pearson"})]
            if n_obs >= 3 else []
        ) + [
            ("descriptives", lambda p: {"variables": [p.get("dependent", "")] + p.get("independents", [])}),
        ],
        "binary_logistic": [
            ("descriptives", lambda p: {"variables": [p.get("dependent", "")] + p.get("independents", [])}),
        ],
        "independent_ttest": [
            ("descriptives", lambda p: {"variables": [p.get("test_var", "")], "group_var": p.get("group_var")}),
        ],
        "one_way_anova": [
            ("descriptives", lambda p: {"variables": [p.get("dep_var", "")], "group_var": p.get("group_var")}),
        ],
        "correlation": [
            ("descriptives", lambda p: {"variables": p.get("variables", [])}),
        ],
    }

    results = None
    executed_method = plan["method"]
    fallback_reason = None
    try:
        results = _execute_plan(plan, df)
        results = _sanitize_results(results)
        _log_pipeline("raw_results_keys", list(results.keys()) if isinstance(results, dict) else type(results).__name__)
    except Exception as e:
        logger.warning(f"[PIPELINE] Primary method {plan['method']} FAILED: {e}")
        original_error = str(e)
        fallback_reason = original_error

        # Try degradation chain
        fallbacks = DEGRADATION_CHAIN.get(plan["method"], [])
        for fallback_method, param_fn in fallbacks:
            try:
                fallback_params = param_fn(plan.get("params", {}))
                # Clean empty strings from variables
                if "variables" in fallback_params:
                    fallback_params["variables"] = [v for v in fallback_params["variables"] if v and v in df.columns]
                fallback_plan = {"method": fallback_method, "params": fallback_params}
                results = _execute_plan(fallback_plan, df)
                results = _sanitize_results(results)
                executed_method = fallback_method
                plan["warnings"] = plan.get("warnings", []) + [
                    f"⚠ {plan['method']} failed ({original_error}) — gracefully degraded to {fallback_method}"
                ]
                logger.info(f"[PIPELINE] Degraded {plan['method']} → {fallback_method}")
                break
            except Exception as e2:
                logger.warning(f"[PIPELINE] Degradation to {fallback_method} also failed: {e2}")
                continue

        if results is None:
            logger.error(f"[PIPELINE] All methods exhausted for {plan['method']}: {original_error}")
            return {
                "status": "error",
                "message": f"Analysis failed: {original_error}",
                "intent": intent,
                "plan": plan,
                "charts": [],
                "tables": [],
            }

    # ── Build decision_trace (Explainable AI) ────────────────────────────
    degraded = executed_method != plan["method"]
    n_vars = len(plan.get("params", {}).get("variables", plan.get("params", {}).get("independents", [])))
    stat_constraints = []
    if n_obs < 3:
        stat_constraints.append(f"Need ≥3 observations for any statistical test, got {n_obs}")
    if n_obs < n_vars + 2 and plan["method"] in ("ols_regression", "binary_logistic"):
        stat_constraints.append(f"Regression requires n ≥ {n_vars + 2} (predictors + intercept + 1 DOF), got {n_obs}")
    if n_obs < 2:
        stat_constraints.append("Variance undefined with n=1 — cannot compute correlation or significance")

    # Confidence score: 0.0 = unusable, 1.0 = solid
    if n_vars > 0:
        confidence = min(1.0, round(n_obs / max(n_vars * 5, 10), 2))
    else:
        confidence = min(1.0, round(n_obs / 30, 2))
    if degraded:
        confidence = round(confidence * 0.5, 2)

    decision_trace = {
        "requested_method": plan["method"],
        "executed_method": executed_method,
        "fallback_triggered": degraded,
        "fallback_reason": fallback_reason,
        "statistical_constraints": stat_constraints,
        "n_observations": n_obs,
        "confidence": confidence,
    }
    _log_pipeline("decision_trace", decision_trace)

    # 4. Build charts + tables from real results (wrapped — never crash on builder bugs)
    try:
        charts = build_charts(executed_method, results, plan.get("params", {}))
    except Exception as e:
        logger.warning(f"[PIPELINE] chart_builder FAILED: {e}")
        charts = []

    try:
        tables = build_tables(executed_method, results, plan.get("params", {}))
    except Exception as e:
        logger.warning(f"[PIPELINE] table_builder FAILED: {e}")
        tables = []
    _log_pipeline("built_output", {
        "n_charts": len(charts),
        "chart_types": [c.get("chart_type") for c in charts],
        "n_tables": len(tables),
        "table_titles": [t.get("title") for t in tables],
    })

    # SAFEGUARD: Warn if no charts/tables were generated
    if not charts and not tables:
        logger.warning(f"[PIPELINE] ⚠ No charts or tables generated for method '{executed_method}'")

    # 5. Generate insight (LLM second pass — constraint-aware)
    try:
        insight = await generate_insight(
            method=executed_method,
            description=plan["description"],
            results=results,
            n_obs=n_obs,
            warnings=plan.get("warnings", []),
            degraded_from=plan["method"] if executed_method != plan["method"] else None,
        )
        _log_pipeline("insight_headline", insight.get("headline", ""))
    except Exception as e:
        logger.warning(f"[PIPELINE] Insight generation FAILED: {e}")
        insight = {"headline": "Analysis complete", "interpretation": "", "significance": "", "recommendations": []}

    response = {
        "status": "success",
        "intent": intent,
        "plan": plan,
        "results": results,
        "insight": insight,
        "charts": charts,
        "tables": tables,
        "decision_trace": decision_trace,
        "meta": {
            "analysis_type": executed_method,
            "original_method": plan["method"],
            "degraded": degraded,
            "confidence": confidence,
            "warnings": plan.get("warnings", []),
        },
    }

    logger.info(f"[PIPELINE] ═══ END analyze → method={executed_method} (planned={plan['method']}), confidence={confidence}, charts={len(charts)}, tables={len(tables)} ═══")
    return response


async def analyze_auto(session_id: str) -> Dict[str, Any]:
    """
    One-click "Analyze for me" pipeline:
    dataset → schema → auto plan → execute all → charts + tables + insights
    """
    logger.info(f"[PIPELINE] ═══ START analyze_auto ═══")

    df, meta = get_session(session_id)
    schema = infer_schema(df)

    plans = plan_auto_analysis(schema, df)
    logger.info(f"[PIPELINE] Auto-generated {len(plans)} analysis plans")

    if not plans:
        return {
            "status": "error",
            "message": "Could not determine suitable analyses for this dataset",
            "dataset_schema": schema,
        }

    analysis_results = []
    for plan in plans:
        try:
            results = _execute_plan(plan, df)
            results = _sanitize_results(results)

            # Build charts + tables per analysis (wrapped)
            try:
                charts = build_charts(plan["method"], results, plan.get("params", {}))
            except Exception:
                charts = []
            try:
                tables = build_tables(plan["method"], results, plan.get("params", {}))
            except Exception:
                tables = []

            # Generate insight
            try:
                insight = await generate_insight(
                    method=plan["method"],
                    description=plan["description"],
                    results=results,
                )
            except Exception:
                insight = {"headline": f"{plan['method']} completed", "interpretation": "", "significance": "", "recommendations": []}

            analysis_results.append({
                "method": plan["method"],
                "description": plan["description"],
                "results": results,
                "insight": insight,
                "charts": charts,
                "tables": tables,
            })
            logger.info(f"[PIPELINE] Auto step: {plan['method']} → charts={len(charts)}, tables={len(tables)}")
        except Exception as e:
            logger.warning(f"[PIPELINE] Auto-analysis step FAILED ({plan['method']}): {e}")
            analysis_results.append({
                "method": plan["method"],
                "description": plan["description"],
                "error": str(e),
                "charts": [],
                "tables": [],
            })

    logger.info(f"[PIPELINE] ═══ END analyze_auto → {len(analysis_results)} results ═══")
    return {
        "status": "success",
        "dataset_schema": schema,
        "n_analyses": len(analysis_results),
        "analyses": analysis_results,
    }


async def generate_full_report(session_id: str, analysis_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate a full structured report.
    If analysis_results is None, runs auto-analysis first.
    """
    df, meta = get_session(session_id)
    schema = infer_schema(df)

    if not analysis_results:
        auto_result = await analyze_auto(session_id)
        analysis_results = auto_result.get("analyses", [])

    report = await generate_report(
        schema_summary=schema["summary_text"],
        analysis_results=analysis_results,
    )

    return {
        "status": "success",
        "report": report,
        "n_analyses": len(analysis_results),
    }


def _execute_plan(plan: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    """Execute a single analysis plan using the stats engine."""
    method = plan["method"]
    params = plan["params"]

    if method == "descriptives":
        group_var = params.get("group_var")
        if group_var and group_var in df.columns:
            # Entity comparison — build comparison-friendly format
            groups = df.groupby(group_var)
            group_names = [str(g) for g in groups.groups.keys()]
            variables = params["variables"]

            # Build comparison rows: each row = [variable, val_entity1, val_entity2, ...]
            comparison_rows = []
            for var in variables:
                if var not in df.columns:
                    continue
                row = [var]
                for gn in group_names:
                    gdf = groups.get_group(gn if gn in groups.groups else list(groups.groups.keys())[group_names.index(gn)])
                    val = gdf[var].mean()
                    row.append(round(val, 4) if pd.notna(val) else "N/A")
                comparison_rows.append(row)

            return {
                "comparison": True,
                "grouped_by": group_var,
                "group_names": group_names,
                "variables": variables,
                "comparison_rows": comparison_rows,
                "rows": [{"variable": var, **{gn: row[i+1] for i, gn in enumerate(group_names)}}
                         for var, row in zip(variables, comparison_rows) if var in df.columns],
            }
        return compute_descriptives(df, params["variables"])

    if method == "frequencies":
        return compute_frequencies(df, params["variable"])

    if method == "crosstabs":
        return compute_crosstabs(df, params["row_var"], params["col_var"])

    if method == "explore":
        return compute_explore(df, params["variable"])

    if method == "independent_ttest":
        return independent_ttest(df, params["group_var"], params["test_var"], params.get("equal_var", True))

    if method == "one_way_anova":
        return one_way_anova(df, params["group_var"], params["dep_var"], params.get("posthoc", "tukey"))

    if method == "correlation":
        return pearson_spearman_correlation(df, params["variables"], params.get("method", "pearson"))

    if method == "ols_regression":
        return ols_regression(df, params["dependent"], params["independents"])

    if method == "binary_logistic":
        return binary_logistic(df, params["dependent"], params["independents"])

    if method == "reliability":
        return run_reliability(df, params["variables"])

    if method == "factor_analysis":
        return run_efa(df, params["variables"], params.get("n_factors", 3), params.get("extraction", "principal"), params.get("rotation", "varimax"))

    raise ValueError(f"Unknown method: {method}")

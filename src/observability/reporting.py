from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a Markdown report from actual Phase 1 pipeline results.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    ragas = metrics.get("ragas", {})
    ragas_status = ragas.get("skipped") or ragas.get("error") or "Completed"
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source and lineage",
        "",
        f"- Source: {source_summary.get('source', '')}",
        f"- Query: `{source_summary.get('query', '')}`",
        f"- Filter: `{source_summary.get('filter', '')}`",
        f"- Raw records: {source_summary.get('raw_records', 0)}",
        f"- Clean records: {source_summary.get('clean_records', 0)}",
        f"- Evaluation questions: {source_summary.get('evaluation_questions', 0)}",
        f"- Run time (UTC): {source_summary.get('run_at_utc', '')}",
        "",
        "## Baseline RAG evaluation",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Samples | {metrics.get('samples', 0)} |",
        f"| Retrieval hit rate | {metrics.get('retrieval_hit_rate', 0.0):.4f} |",
        f"| Mean token F1 | {metrics.get('mean_token_f1', 0.0):.4f} |",
        f"| Judge accuracy | {metrics.get('judge_accuracy', 0.0):.4f} |",
        f"| Mean judge score | {metrics.get('mean_judge_score', 0.0):.4f} |",
        "",
        f"Ragas: {ragas_status}",
        "",
        "## Data quality gate",
        "",
        f"- Overall success: **{quality.get('success', False)}**",
        f"- Great Expectations success: {quality.get('gx_success', False)}",
        f"- GX validations executed: {quality.get('expectation_count', 0)}",
        "",
        "## Freshness SLA",
        "",
        f"- Fresh: **{freshness.get('is_fresh', False)}**",
        f"- Threshold: {freshness.get('threshold_days', 0)} days",
        f"- Stale rows: {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)}",
        f"- Stale ratio: {freshness.get('stale_ratio', 0.0):.2%}",
        f"- Oldest publication: {freshness.get('oldest_published')}",
        f"- Latest publication: {freshness.get('latest_published')}",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the measured baseline/corrupted/repaired comparison report."""
    metric_rows = [
        ("Retrieval hit rate", "retrieval_hit_rate"),
        ("Mean token F1", "mean_token_f1"),
        ("Judge accuracy", "judge_accuracy"),
        ("Mean judge score", "mean_judge_score"),
    ]
    lines = [
        "# Corruption Impact and Recovery Report",
        "",
        "## Three-state performance comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, key in metric_rows:
        baseline = float(baseline_metrics.get(key, 0.0))
        corrupted = float(corrupted_metrics.get(key, 0.0))
        repaired = float(repaired_metrics.get(key, 0.0))
        lines.append(
            f"| {label} | {baseline:.4f} | {corrupted:.4f} | {repaired:.4f} "
            f"| {corrupted - baseline:+.4f} | {repaired - corrupted:+.4f} |"
        )

    lines.extend(
        [
            "",
            "## Quality and freshness comparison",
            "",
            "| Signal | Corrupted | Repaired |",
            "| --- | ---: | ---: |",
            f"| GX quality gate | {corrupted_quality.get('gx_success', False)} | {repaired_quality.get('gx_success', False)} |",
            f"| Overall quality + freshness | {corrupted_quality.get('success', False)} | {repaired_quality.get('success', False)} |",
            f"| Freshness SLA | {corrupted_freshness.get('is_fresh', False)} | {repaired_freshness.get('is_fresh', False)} |",
            f"| Stale rows | {corrupted_freshness.get('stale_rows', 0)} | {repaired_freshness.get('stale_rows', 0)} |",
            f"| Stale ratio | {corrupted_freshness.get('stale_ratio', 0.0):.2%} | {repaired_freshness.get('stale_ratio', 0.0):.2%} |",
            "",
            "## Interpretation",
            "",
            "The corrupted state demonstrates a silent failure: the pipeline remains executable and can still return answers, while retrieval/answer metrics and automated data-quality signals deteriorate. The repaired state is rebuilt idempotently from the preserved raw snapshot, restoring the clean schema, freshness, and baseline behavior without trusting corrupted derived artifacts.",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))

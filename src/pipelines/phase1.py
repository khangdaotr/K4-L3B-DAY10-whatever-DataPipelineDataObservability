from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import Settings, load_settings
from core.utils import read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Run the complete baseline pipeline and return its generated results."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    run_date = datetime.now(UTC)
    clean_df = build_clean_dataframe(records, run_date)
    if clean_df.empty:
        raise ValueError("Phase 1 cannot continue because cleaning produced no valid records.")
    write_csv(clean_df, settings.paths.clean_csv)
    settings.paths.clean_json.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_json(
        settings.paths.clean_json,
        orient="records",
        indent=2,
        force_ascii=False,
    )

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, stage="baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "evaluation_questions": len(test_set),
        "run_at_utc": run_date.isoformat(),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    return {
        "source_summary": source_summary,
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
        "report_path": str(settings.paths.baseline_report),
    }


def main() -> None:
    """Run Phase 1 with environment-backed project settings.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    result = run_phase1_pipeline(load_settings())
    metrics = result["metrics"]
    print("Phase 1 completed successfully.")
    print(f"Clean records: {result['source_summary']['clean_records']}")
    print(f"Evaluation questions: {result['source_summary']['evaluation_questions']}")
    print(f"Retrieval hit rate: {metrics['retrieval_hit_rate']:.4f}")
    print(f"Mean token F1: {metrics['mean_token_f1']:.4f}")
    print(f"Quality gate: {result['quality']['success']}")
    print(f"Report: {result['report_path']}")

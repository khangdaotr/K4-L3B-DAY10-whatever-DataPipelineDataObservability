from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
from great_expectations import expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def evaluate_freshness_sla(
    df: pd.DataFrame,
    threshold_days: int = 180,
    max_stale_ratio: float = 0.25,
) -> dict[str, Any]:
    """Evaluate the proportion of records older than the freshness threshold."""
    total_rows = len(df)
    ages = (
        pd.to_numeric(df["age_days"], errors="coerce")
        if "age_days" in df.columns
        else pd.Series(index=df.index, dtype="float64")
    )
    stale_rows = int(ages.gt(threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    invalid_age_rows = int(ages.isna().sum())
    is_fresh = total_rows > 0 and invalid_age_rows == 0 and stale_ratio <= max_stale_ratio
    return {
        "threshold_days": threshold_days,
        "max_stale_ratio": max_stale_ratio,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": stale_ratio,
        "invalid_age_rows": invalid_age_rows,
        "is_fresh": is_fresh,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, stage: str) -> dict[str, Any]:
    """Run GX 1.x quality gates and the freshness SLA, then persist a report.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        *[
            gxe.ExpectColumnValuesToNotBeNull(column=column)
            for column in ("paper_id", "title", "text_for_embedding")
        ],
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    validations = [batch.validate(expectation, result_format="SUMMARY") for expectation in expectations]
    validation_payloads = [validation.to_json_dict() for validation in validations]
    gx_success = all(bool(validation.success) for validation in validations)

    freshness = evaluate_freshness_sla(
        df,
        threshold_days=settings.freshness_threshold_days,
        max_stale_ratio=0.25,
    )
    payload = {
        "stage": stage,
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "freshness_success": freshness["is_fresh"],
        "expectation_count": len(validations),
        "expectations": validation_payloads,
        "freshness": freshness,
    }
    stage_key = stage.casefold()
    if "corrupt" in stage_key:
        report_path = settings.paths.corrupted_quality_report
    elif "repair" in stage_key:
        report_path = settings.paths.repaired_quality_report
    else:
        report_path = settings.paths.baseline_quality_report
    write_json(report_path, payload)
    return payload


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: Path
) -> dict[str, Any]:
    """Build and persist a freshness report with publication-date bounds.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    payload = evaluate_freshness_sla(
        df,
        threshold_days=settings.freshness_threshold_days,
        max_stale_ratio=0.25,
    )
    published = (
        pd.to_datetime(df["published"], errors="coerce", utc=True)
        if "published" in df.columns
        else pd.Series(index=df.index, dtype="datetime64[ns, UTC]")
    )
    valid_dates = published.dropna()
    payload.update(
        {
            "latest_published": (
                valid_dates.max().strftime("%Y-%m-%d") if not valid_dates.empty else None
            ),
            "oldest_published": (
                valid_dates.min().strftime("%Y-%m-%d") if not valid_dates.empty else None
            ),
        }
    )
    write_json(report_path, payload)
    return payload

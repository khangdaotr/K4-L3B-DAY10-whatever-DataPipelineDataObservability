from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import Settings
from core.utils import write_csv
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records


def repair_from_raw_snapshot(
    settings: Settings, run_date: datetime | None = None
) -> pd.DataFrame:
    """Idempotently rebuild clean artifacts from the immutable raw-record snapshot."""
    if not settings.paths.raw_records_json.is_file():
        raise FileNotFoundError(
            f"Cannot repair without raw snapshot: {settings.paths.raw_records_json}"
        )
    records = load_raw_records(settings.paths.raw_records_json)
    repaired = build_clean_dataframe(records, run_date or datetime.now(UTC))
    if repaired.empty:
        raise ValueError("Repair produced no valid records from the raw snapshot.")

    write_csv(repaired, settings.paths.repaired_clean_csv)
    settings.paths.repaired_clean_json.parent.mkdir(parents=True, exist_ok=True)
    repaired.to_json(
        settings.paths.repaired_clean_json,
        orient="records",
        indent=2,
        force_ascii=False,
    )
    return repaired

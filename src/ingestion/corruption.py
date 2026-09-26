from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


NOISE_PREFIX = "@@@ CORRUPTED_NOISE_7F3A ###"


def _json_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _row_snapshot(row: pd.Series) -> dict[str, Any]:
    return {column: _json_value(value) for column, value in row.to_dict().items()}


def _rebuild_embedding_text(df: pd.DataFrame) -> None:
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Inject six deterministic corruption scenarios and log every affected row.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "published",
        "age_days",
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "text_for_embedding",
    }
    missing = sorted(required_columns.difference(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing required columns: {missing}")
    if len(df) < 10:
        raise ValueError("At least 10 clean rows are required to inject all six corruption types.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    events: list[dict[str, Any]] = []

    # 1. Remove the newest 20% of the input records.
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_count = max(1, ceil(len(corrupted) * 0.20))
    drop_indices = published.sort_values(ascending=False, na_position="last").index[:drop_count]
    for index in drop_indices:
        row = corrupted.loc[index]
        events.append(
            {
                "corruption_type": "drop_latest_records",
                "paper_id": str(row["paper_id"]),
                "source_row_index": int(index),
                "before": _row_snapshot(row),
                "after": None,
            }
        )
    corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)

    # Use separate rows for each mutation so every injected failure is easy to
    # identify and explain in the resulting lineage log.
    mutation_size = max(1, min(2, len(corrupted) // 5))
    stale_count = max(1, ceil((len(corrupted) + mutation_size) * 0.26))
    stale_start = mutation_size * 3
    groups = {
        "blank_summary": list(range(0, mutation_size)),
        "inject_noise": list(range(mutation_size, mutation_size * 2)),
        "truncate_title": list(range(mutation_size * 2, mutation_size * 3)),
        "stale_date": list(range(stale_start, min(stale_start + stale_count, len(corrupted)))),
    }
    pending_events: list[tuple[dict[str, Any], int]] = []

    for corruption_type, indices in groups.items():
        for index in indices:
            before = _row_snapshot(corrupted.loc[index])
            if corruption_type == "blank_summary":
                corrupted.at[index, "summary"] = ""
            elif corruption_type == "inject_noise":
                corrupted.at[index, "summary"] = (
                    f"{NOISE_PREFIX} {corrupted.at[index, 'summary']}"
                )
            elif corruption_type == "truncate_title":
                original = str(corrupted.at[index, "title"])
                corrupted.at[index, "title"] = (original[:7] or "BAD")[:7]
            else:
                original_date = pd.to_datetime(corrupted.at[index, "published"], utc=True)
                corrupted.at[index, "published"] = (
                    original_date - pd.Timedelta(days=365)
                ).strftime("%Y-%m-%d")
                corrupted.at[index, "age_days"] = int(corrupted.at[index, "age_days"]) + 365

            event = {
                "corruption_type": corruption_type,
                "paper_id": str(corrupted.at[index, "paper_id"]),
                "source_row_index": int(index),
                "before": before,
            }
            pending_events.append((event, index))

    _rebuild_embedding_text(corrupted)
    for event, index in pending_events:
        event["after"] = _row_snapshot(corrupted.loc[index])
        events.append(event)

    # 6. Append exact copies after all derived fields have been rebuilt.
    duplicate_start = stale_start + len(groups["stale_date"])
    duplicate_indices = list(
        range(duplicate_start, min(duplicate_start + mutation_size, len(corrupted)))
    )
    if not duplicate_indices:
        duplicate_indices = [len(corrupted) - 1]
    duplicates = corrupted.loc[duplicate_indices].copy(deep=True)
    for index, (_, row) in zip(duplicate_indices, duplicates.iterrows(), strict=True):
        events.append(
            {
                "corruption_type": "duplicate_rows",
                "paper_id": str(row["paper_id"]),
                "source_row_index": int(index),
                "before": _row_snapshot(row),
                "after": _row_snapshot(row),
            }
        )
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)

    write_json(output_log_path, events)
    return corrupted

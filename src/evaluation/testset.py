from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


QUESTION_TYPES = ("summary", "authors", "date", "categories")


def _as_date_string(value: object) -> str:
    timestamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(timestamp):
        return ""
    return timestamp.strftime("%Y-%m-%d")


def _question_and_answer(row: pd.Series, question_type: str) -> tuple[str, str]:
    title = normalize_whitespace(str(row["title"]))
    if question_type == "summary":
        return (
            f"What is the summary of the paper '{title}'?",
            first_sentence(str(row["summary"])),
        )
    if question_type == "authors":
        return (
            f"Who authored the paper '{title}'?",
            normalize_whitespace(str(row["authors_joined"])),
        )
    if question_type == "date":
        return (
            f"When was the paper '{title}' published?",
            _as_date_string(row["published"]),
        )
    return (
        f"What categories does the paper '{title}' belong to?",
        normalize_whitespace(str(row.get("categories_joined", "")))
        or normalize_whitespace(str(row.get("primary_category", "")))
        or "Uncategorized",
    )


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build a deterministic, balanced ten-question ground-truth set.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "published",
    }
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {missing_columns}")

    candidates = df.copy()
    for column in required_columns:
        candidates = candidates[candidates[column].notna()]
        if column != "published":
            candidates = candidates[candidates[column].astype(str).str.strip().ne("")]
    valid_dates = candidates["published"].map(lambda value: bool(_as_date_string(value)))
    candidates = candidates.loc[valid_dates]
    candidates = candidates.drop_duplicates(subset="paper_id", keep="first")
    candidates = candidates.sort_values("paper_id", kind="stable").reset_index(drop=True)
    if len(candidates) < 10:
        raise ValueError(
            "At least 10 complete, unique papers are required to build the evaluation set; "
            f"found {len(candidates)}."
        )

    test_set: list[dict[str, Any]] = []
    for index, (_, row) in enumerate(candidates.head(10).iterrows(), start=1):
        question_type = QUESTION_TYPES[(index - 1) % len(QUESTION_TYPES)]
        question, ground_truth = _question_and_answer(row, question_type)
        test_set.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [normalize_whitespace(str(row["paper_id"]))],
            }
        )

    write_json(output_path, test_set)
    return test_set

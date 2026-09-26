from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
import re

import pandas as pd

from ingestion.crossref import PaperRecord


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _normalize_text(value: object) -> str:
    """Strip HTML/JATS markup and collapse all whitespace to single spaces."""
    if not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(unescape(value))
        parser.close()
        value = " ".join(parser.parts)
    except Exception:
        value = re.sub(r"<[^>]+>", " ", unescape(value))
    return re.sub(r"\s+", " ", value).strip()


def _normalize_list(values: object) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_text(value)
        key = text.casefold()
        if text and key not in seen:
            normalized.append(text)
            seen.add(key)
    return normalized


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw paper records into an embedding-ready dataframe.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    base_columns = [field.name for field in PaperRecord.__dataclass_fields__.values()]
    output_columns = [
        *base_columns,
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "age_days",
        "text_for_embedding",
    ]
    if not records:
        return pd.DataFrame(columns=output_columns)

    df = pd.DataFrame(asdict(record) for record in records)

    text_columns = [
        "paper_id",
        "title",
        "summary",
        "primary_category",
        "abs_url",
        "pdf_url",
        "comment",
    ]
    for column in text_columns:
        df[column] = df[column].map(_normalize_text)
    df["paper_id"] = df["paper_id"].str.lower()
    df["authors"] = df["authors"].map(_normalize_list)
    df["categories"] = df["categories"].map(_normalize_list).map(
        lambda values: values or ["Uncategorized"]
    )
    df["primary_category"] = df.apply(
        lambda row: row["primary_category"]
        or (row["categories"][0] if row["categories"] else ""),
        axis=1,
    )

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    updated = pd.to_datetime(df["updated"], errors="coerce", utc=True).fillna(published)
    df["_published_dt"] = published
    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")

    # Empty essential fields and invalid publication dates cannot produce a
    # trustworthy embedding record or freshness value.
    valid = (
        df["paper_id"].ne("")
        & df["title"].ne("")
        & df["summary"].ne("")
        & df["_published_dt"].notna()
    )
    df = df.loc[valid].copy()
    df = df.drop_duplicates(subset="paper_id", keep="first")
    if df.empty:
        return pd.DataFrame(columns=output_columns)

    df["authors_joined"] = df["authors"].map(lambda values: ", ".join(values))
    df["categories_joined"] = df["categories"].map(lambda values: ", ".join(values))
    df["summary_chars"] = df["summary"].str.len().astype("int64")

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    df["age_days"] = (run_timestamp.normalize() - df["_published_dt"].dt.normalize()).dt.days

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

    df = df.sort_values(["_published_dt", "paper_id"], ascending=[False, True])
    return df.drop(columns="_published_dt").reset_index(drop=True)[output_columns]

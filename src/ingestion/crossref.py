from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


class _TextExtractor(HTMLParser):
    """Small, dependency-free HTML/JATS-to-text converter."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(unescape(value))
        parser.close()
        text = " ".join(parser.parts)
    except Exception:
        # Crossref abstracts are usually JATS fragments. This keeps malformed
        # fragments usable without allowing markup to leak into the record.
        text = re.sub(r"<[^>]+>", " ", unescape(value))
    return re.sub(r"\s+", " ", text).strip()


def _first_text(value: object) -> str:
    if isinstance(value, list):
        return _clean_text(value[0]) if value else ""
    return _clean_text(value)


def _date_from_parts(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        return ""
    try:
        numbers = [int(part) for part in parts[0][:3]]
        if not numbers:
            return ""
        year = numbers[0]
        month = numbers[1] if len(numbers) > 1 else 1
        day = numbers[2] if len(numbers) > 2 else 1
        return date(year, month, day).isoformat()
    except (TypeError, ValueError):
        return ""


def _crossref_date(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        from_parts = _date_from_parts(value)
        if from_parts:
            return from_parts
        if isinstance(value, dict):
            date_time = value.get("date-time")
            if isinstance(date_time, str) and len(date_time) >= 10:
                try:
                    return date.fromisoformat(date_time[:10]).isoformat()
                except ValueError:
                    pass
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref work-list payload into normalized paper records.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    seen_dois: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _clean_text(item.get("DOI")).lower()
        title = _first_text(item.get("title"))
        summary = _clean_text(item.get("abstract"))
        if not doi or not title or not summary or doi in seen_dois:
            continue

        authors: list[str] = []
        raw_authors = item.get("author", [])
        if isinstance(raw_authors, list):
            for author in raw_authors:
                if not isinstance(author, dict):
                    continue
                name = _clean_text(author.get("name"))
                if not name:
                    name = " ".join(
                        part
                        for part in (
                            _clean_text(author.get("given")),
                            _clean_text(author.get("family")),
                        )
                        if part
                    )
                if name:
                    authors.append(name)

        raw_subjects = item.get("subject", [])
        categories = (
            [subject for value in raw_subjects if (subject := _clean_text(value))]
            if isinstance(raw_subjects, list)
            else []
        )
        published = _crossref_date(
            item, ("published", "published-print", "published-online", "issued", "created")
        )
        updated = _crossref_date(item, ("updated", "indexed", "deposited", "created")) or published

        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{doi}"
        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if not isinstance(link, dict):
                    continue
                content_type = str(link.get("content-type", "")).lower()
                if "pdf" in content_type:
                    pdf_url = _clean_text(link.get("URL"))
                    if pdf_url:
                        break
        pdf_url = pdf_url or abs_url

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {doi}",
            )
        )
        seen_dois.add(doi)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data, falling back to the local raw snapshot on failure.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    raw_path = settings.paths.raw_api_response
    records_path = settings.paths.raw_records_json
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))

    try:
        response = session.get(
            "https://api.crossref.org/works",
            params={
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            },
            headers={"User-Agent": "data-observability-lab/0.1 (Crossref metadata ingestion)"},
            timeout=(5, 30),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Crossref response must be a JSON object.")
        # Preserve the successful response bytes, rather than serializing the
        # parsed object, so this file remains a true lineage anchor.
        raw_path.write_bytes(response.content)
    except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
        if not raw_path.is_file():
            raise RuntimeError("Crossref request failed and no offline snapshot exists.") from exc
        try:
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as snapshot_exc:
            raise RuntimeError("Crossref request failed and the offline snapshot is invalid.") from snapshot_exc

    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref payload did not contain any valid records.")
    records_path.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a normalized raw-record snapshot into `PaperRecord` objects."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")
    try:
        return [PaperRecord(**item) for item in payload if isinstance(item, dict)]
    except TypeError as exc:
        raise ValueError(f"Raw records file has an invalid PaperRecord: {path}") from exc

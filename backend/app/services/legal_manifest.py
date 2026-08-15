"""Legal manifest validation and offline metadata import.

The Markdown files in ``docs/legal`` are the single source of legal text.  The
manifest binds each public route to one of those files and its SHA-256 digest.
Development material is deliberately usable only outside production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models import LegalDocument
from app.models.legal import DOCUMENT_KINDS

RUNTIME_DOCUMENT_KINDS = (*DOCUMENT_KINDS, "cookie_storage_notice")
_PATH = re.compile(r"^/[A-Za-z0-9._~/-]+$")
_SOURCE_PATH = re.compile(r"^docs/legal/[a-z0-9-]+\.md$")
_VERSION = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDER = re.compile(r"\[[^\]\r\n]+\]")


def _resolve_runtime_root() -> Path:
    """Find the repository root in source checkouts and the production image.

    The source checkout stores the manifest under ``backend/``. The backend image
    packages the same manifest at ``/app/legal_manifest.json`` and the legal sources
    at ``/app/docs/legal``. Requiring both the manifest and source directory prevents
    a partial image from accidentally passing path resolution.
    """

    module_path = Path(__file__).resolve()
    candidates = (module_path.parents[3], module_path.parents[2])
    for candidate in candidates:
        source_root = candidate / "docs" / "legal"
        if (candidate / "backend" / "legal_manifest.json").is_file() and source_root.is_dir():
            return candidate
        if (candidate / "legal_manifest.json").is_file() and source_root.is_dir():
            return candidate
    return candidates[0]


_ROOT = _resolve_runtime_root()
_DEFAULT_MANIFEST_PATH = (
    _ROOT / "backend" / "legal_manifest.json"
    if (_ROOT / "backend" / "legal_manifest.json").is_file()
    else _ROOT / "legal_manifest.json"
)


def validate_item(item: dict[str, Any]) -> dict[str, Any]:
    required = {
        "kind",
        "version",
        "title",
        "publicPath",
        "sourcePath",
        "contentSha256",
        "effectiveAt",
        "requiredAtRegistration",
        "isDraft",
    }
    if set(item) != required:
        raise ValueError("manifest item has unsupported or missing fields")
    if item["kind"] not in RUNTIME_DOCUMENT_KINDS or not _VERSION.fullmatch(item["version"]):
        raise ValueError("invalid kind or version")
    if not isinstance(item["title"], str) or not item["title"].strip() or len(item["title"]) > 255:
        raise ValueError("invalid title")
    path = item["publicPath"]
    if not isinstance(path, str) or not _PATH.fullmatch(path) or ".." in path or "\\" in path:
        raise ValueError("invalid publicPath")
    source_path = item["sourcePath"]
    if not isinstance(source_path, str) or not _SOURCE_PATH.fullmatch(source_path):
        raise ValueError("invalid sourcePath")
    digest = item["contentSha256"]
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("invalid contentSha256")
    if not isinstance(item["requiredAtRegistration"], bool) or not isinstance(
        item["isDraft"], bool
    ):
        raise ValueError("invalid manifest boolean")
    if item["kind"] == "cookie_storage_notice" and item["requiredAtRegistration"]:
        raise ValueError("cookie notice cannot be required at registration")
    try:
        effective_at = datetime.fromisoformat(item["effectiveAt"].replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid effectiveAt") from exc
    if effective_at.tzinfo is None:
        raise ValueError("effectiveAt requires timezone")
    return {**item, "effectiveAt": effective_at.astimezone(UTC)}


def load_runtime_manifest(manifest_path: Path | None = None) -> list[dict[str, Any]]:
    path = manifest_path or _DEFAULT_MANIFEST_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("legal manifest cannot be read") from exc
    if not isinstance(raw, list):
        raise ValueError("manifest root must be a list")
    parsed = [validate_item(item) for item in raw]
    if {item["kind"] for item in parsed} != set(RUNTIME_DOCUMENT_KINDS):
        raise ValueError("manifest must contain exactly one entry for every legal document")
    if len({item["publicPath"] for item in parsed}) != len(parsed):
        raise ValueError("duplicate publicPath")
    return parsed


def validate_runtime_manifest(
    *, environment: str, manifest_path: Path | None = None, root: Path | None = None
) -> list[dict[str, Any]]:
    """Verify source linkage and refuse incomplete legal material in production."""
    root = root or _ROOT
    parsed = load_runtime_manifest(manifest_path)
    for item in parsed:
        source = root / item["sourcePath"]
        try:
            content = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"legal source is unavailable: {item['kind']}") from exc
        actual_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if actual_digest != item["contentSha256"]:
            raise ValueError(f"legal content hash mismatch: {item['kind']}")
        if environment == "production" and (
            item["isDraft"]
            or "DEV" in content.upper()
            or "НЕ ФИНАЛ" in content.upper()
            or _PLACEHOLDER.search(content) is not None
        ):
            raise ValueError(f"production legal document is not finalized: {item['kind']}")
    return parsed


def get_runtime_document(kind: str, *, environment: str) -> dict[str, Any]:
    documents = validate_runtime_manifest(environment=environment)
    try:
        item = next(document for document in documents if document["kind"] == kind)
    except StopIteration as exc:
        raise ValueError("unknown legal document") from exc
    content = (_ROOT / item["sourcePath"]).read_text(encoding="utf-8")
    return {**item, "content": content}


def import_manifest(session, items: list[dict[str, Any]], *, dry_run: bool) -> dict[str, int]:
    try:
        parsed = [validate_item(item) for item in items]
        database_items = [item for item in parsed if item["kind"] in DOCUMENT_KINDS]
        if any(item["effectiveAt"] > datetime.now(UTC) for item in database_items):
            raise ValueError("future effectiveAt cannot be activated by this importer")
        if len({(item["kind"], item["version"]) for item in database_items}) != len(database_items):
            raise ValueError("duplicate kind/version")
        if len({item["kind"] for item in database_items}) != len(database_items):
            raise ValueError("only one active document per kind may be imported")
        counts = {"created": 0, "unchanged": 0, "retired": 0}
        for item in database_items:
            existing = session.scalar(
                select(LegalDocument).where(
                    LegalDocument.kind == item["kind"], LegalDocument.version == item["version"]
                )
            )
            if existing:
                if existing.retired_at is not None:
                    raise ValueError("retired document versions cannot be reactivated")
                if (
                    existing.title,
                    existing.public_path,
                    existing.content_sha256,
                    _as_utc(existing.effective_at),
                    existing.required_at_registration,
                ) != (
                    item["title"],
                    item["publicPath"],
                    item["contentSha256"],
                    item["effectiveAt"],
                    item["requiredAtRegistration"],
                ):
                    raise ValueError("existing document metadata does not match manifest")
                counts["unchanged"] += 1
            old = session.scalars(
                select(LegalDocument).where(
                    LegalDocument.kind == item["kind"],
                    LegalDocument.retired_at.is_(None),
                    LegalDocument.version != item["version"],
                )
            ).all()
            if old and not dry_run:
                for document in old:
                    document.retired_at = item["effectiveAt"]
                session.flush()
            if existing is None:
                if not dry_run:
                    session.add(
                        LegalDocument(
                            kind=item["kind"],
                            version=item["version"],
                            title=item["title"],
                            public_path=item["publicPath"],
                            content_sha256=item["contentSha256"],
                            effective_at=item["effectiveAt"],
                            required_at_registration=item["requiredAtRegistration"],
                        )
                    )
                counts["created"] += 1
            counts["retired"] += len(old)
        return counts
    except Exception:
        session.rollback()
        raise


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import local legal metadata manifest")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        items = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError("manifest root must be a list")
        validate_runtime_manifest(environment="local", manifest_path=args.manifest)
        with get_session_factory()() as session:
            counts = import_manifest(session, items, dry_run=args.dry_run)
            if not args.dry_run:
                session.commit()
        print(json.dumps(counts, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

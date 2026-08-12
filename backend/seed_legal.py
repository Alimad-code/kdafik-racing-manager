"""Import the checked runtime manifest into the legal-document metadata table."""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.legal_manifest import import_manifest, validate_runtime_manifest

manifest_path = Path(__file__).with_name("legal_manifest.json")
environment = get_settings().environment
validate_runtime_manifest(environment=environment, manifest_path=manifest_path)
items = json.loads(manifest_path.read_text(encoding="utf-8"))

with get_session_factory()() as session:
    counts = import_manifest(session, items, dry_run=False)
    session.commit()
    print(f"Imported legal metadata: {counts}")

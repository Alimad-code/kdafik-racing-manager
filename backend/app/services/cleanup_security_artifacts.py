"""Run bounded technical cleanup: python -m app.services.cleanup_security_artifacts."""

from __future__ import annotations

import argparse
import json

from app.db.session import get_session_factory
from app.services.user_data import SecurityArtifactCleanup


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge stale security artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 10_000:
        parser.error("--batch-size must be between 1 and 10000")
    with get_session_factory()() as session:
        cleanup = SecurityArtifactCleanup(session, batch_size=args.batch_size)
        counts = cleanup.run(dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()

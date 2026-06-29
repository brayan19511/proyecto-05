"""Run the initial security seed without requiring an authenticated API user."""

import json

from app.api.verify.seed_service import SeedService
from app.core.db.db_postgres import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        result = SeedService(db).run_seed()
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()

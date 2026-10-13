"""
One-off migration: data/*.json -> the SQLAlchemy database.

    python scripts/migrate_json_to_db.py

Idempotent — re-running will not duplicate rows, and article view counts
carry over. The JSON files are left in place as a backup.

The app also seeds an empty database on boot (see seed.py), so this is only
needed to import data into a database that already has some content, or to
run the import deliberately rather than as a side effect of starting up.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from seed import seed_all  # noqa: E402


def main():
    # AUTO_SEED off: this script does the seeding explicitly, and reporting
    # "+0" for rows the boot hook had already inserted would be misleading.
    os.environ["AUTO_SEED"] = "0"

    app = create_app()

    with app.app_context():
        db.create_all()

        print("Migrating data/*.json -> database")
        print(f"  database: {app.config['SQLALCHEMY_DATABASE_URI']}")

        for name, count in seed_all(app.logger).items():
            print(f"  {name:<9} +{count}")

        print("Done. The JSON files were left in place as a backup.")


if __name__ == "__main__":
    main()

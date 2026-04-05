"""Import seed data from CSV files into the database."""

import csv
import sys
import time

from peewee import chunked

from app import create_app
from app.database import db
from app.models import Event, Url, User


def parse_bool(value):
    """Convert string 'True'/'False' to Python bool."""
    return value.strip().lower() == "true"


def load_csv(filepath):
    """Read a CSV file and return list of dicts."""
    with open(filepath, newline="") as f:
        return list(csv.DictReader(f))


def import_users(rows):
    """Import user records."""
    data = [
        {
            "id": int(r["id"]),
            "username": r["username"],
            "email": r["email"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    with db.atomic():
        for batch in chunked(data, 100):
            User.insert_many(batch).execute()
    return len(data)


def import_urls(rows):
    """Import URL records."""
    data = [
        {
            "id": int(r["id"]),
            "user_id": int(r["user_id"]),
            "short_code": r["short_code"],
            "original_url": r["original_url"],
            "title": r["title"],
            "is_active": parse_bool(r["is_active"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    with db.atomic():
        for batch in chunked(data, 100):
            Url.insert_many(batch).execute()
    return len(data)


def import_events(rows):
    """Import event records."""
    data = [
        {
            "id": int(r["id"]),
            "url_id": int(r["url_id"]),
            "user_id": int(r["user_id"]),
            "event_type": r["event_type"],
            "timestamp": r["timestamp"],
            "details": r["details"],
        }
        for r in rows
    ]
    with db.atomic():
        for batch in chunked(data, 100):
            Event.insert_many(batch).execute()
    return len(data)


def seed(csv_dir="csvs"):
    """Run full seed import. Returns dict of counts."""
    start = time.time()

    users = load_csv(f"{csv_dir}/users.csv")
    urls = load_csv(f"{csv_dir}/urls.csv")
    events = load_csv(f"{csv_dir}/events.csv")

    user_count = import_users(users)
    url_count = import_urls(urls)
    event_count = import_events(events)

    elapsed = time.time() - start

    return {
        "users": user_count,
        "urls": url_count,
        "events": event_count,
        "elapsed_seconds": round(elapsed, 2),
    }


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_tables([User, Url, Event])

        if User.select().count() > 0:
            print("Database already has data. Skipping seed.")
            sys.exit(0)

        result = seed()

        # Reset PostgreSQL sequences after bulk insert with explicit IDs
        for table in ("users", "urls", "events"):
            db.execute_sql(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"(SELECT MAX(id) FROM {table}))"
            )

        print(
            f"Imported {result['users']} users, {result['urls']} urls, "
            f"{result['events']} events in {result['elapsed_seconds']}s"
        )

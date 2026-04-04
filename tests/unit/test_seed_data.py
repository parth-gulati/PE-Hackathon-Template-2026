"""Unit tests for CSV seed data import."""

import os

import pytest
from peewee import SqliteDatabase

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from seed_data import import_events, import_urls, import_users, load_csv, parse_bool, seed

test_db = SqliteDatabase(":memory:")
FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def setup_module():
    db.initialize(test_db)
    test_db.bind([User, Url, Event])
    test_db.connect()
    test_db.create_tables([User, Url, Event])


def teardown_module():
    test_db.drop_tables([Event, Url, User])
    test_db.close()


@pytest.fixture(autouse=True)
def clean_tables():
    """Drop and recreate tables before each test for clean state."""
    test_db.drop_tables([Event, Url, User])
    test_db.create_tables([User, Url, Event])
    yield


class TestParseBool:
    def test_true(self):
        assert parse_bool("True") is True

    def test_false(self):
        assert parse_bool("False") is False

    def test_case_insensitive(self):
        assert parse_bool("true") is True
        assert parse_bool("FALSE") is False

    def test_whitespace(self):
        assert parse_bool(" True ") is True


class TestLoadCsv:
    def test_load_users_csv(self):
        rows = load_csv(f"{FIXTURES}/users.csv")
        assert len(rows) == 2
        assert rows[0]["username"] == "testuser1"
        assert rows[0]["email"] == "test1@example.com"

    def test_load_urls_csv(self):
        rows = load_csv(f"{FIXTURES}/urls.csv")
        assert len(rows) == 2
        assert rows[0]["short_code"] == "AbCdEf"

    def test_load_events_csv(self):
        rows = load_csv(f"{FIXTURES}/events.csv")
        assert len(rows) == 2
        assert rows[0]["event_type"] == "created"


class TestImportUsers:
    def test_imports_all_users(self):
        rows = load_csv(f"{FIXTURES}/users.csv")
        count = import_users(rows)
        assert count == 2
        assert User.select().count() == 2

    def test_user_fields_correct(self):
        rows = load_csv(f"{FIXTURES}/users.csv")
        import_users(rows)
        user = User.get_by_id(1)
        assert user.username == "testuser1"
        assert user.email == "test1@example.com"


class TestImportUrls:
    def test_imports_all_urls(self):
        import_users(load_csv(f"{FIXTURES}/users.csv"))
        rows = load_csv(f"{FIXTURES}/urls.csv")
        count = import_urls(rows)
        assert count == 2
        assert Url.select().count() == 2

    def test_url_fields_correct(self):
        import_users(load_csv(f"{FIXTURES}/users.csv"))
        import_urls(load_csv(f"{FIXTURES}/urls.csv"))
        url = Url.get_by_id(1)
        assert url.short_code == "AbCdEf"
        assert url.original_url == "https://example.com/page1"
        assert url.is_active is True

    def test_is_active_false_parsed(self):
        import_users(load_csv(f"{FIXTURES}/users.csv"))
        import_urls(load_csv(f"{FIXTURES}/urls.csv"))
        url = Url.get_by_id(2)
        assert url.is_active is False


class TestImportEvents:
    def test_imports_all_events(self):
        import_users(load_csv(f"{FIXTURES}/users.csv"))
        import_urls(load_csv(f"{FIXTURES}/urls.csv"))
        rows = load_csv(f"{FIXTURES}/events.csv")
        count = import_events(rows)
        assert count == 2
        assert Event.select().count() == 2

    def test_event_fields_correct(self):
        import_users(load_csv(f"{FIXTURES}/users.csv"))
        import_urls(load_csv(f"{FIXTURES}/urls.csv"))
        import_events(load_csv(f"{FIXTURES}/events.csv"))
        event = Event.get_by_id(1)
        assert event.event_type == "created"
        assert event.url_id == 1
        assert event.user_id == 1
        assert "AbCdEf" in event.details


class TestSeedFunction:
    def test_seed_imports_all_tables(self):
        result = seed(csv_dir=FIXTURES)
        assert result["users"] == 2
        assert result["urls"] == 2
        assert result["events"] == 2
        assert result["elapsed_seconds"] >= 0

    def test_seed_transactional(self):
        """Verify data is consistent after seed."""
        seed(csv_dir=FIXTURES)
        assert User.select().count() == 2
        assert Url.select().count() == 2
        assert Event.select().count() == 2
        # Verify FK integrity
        url = Url.get_by_id(1)
        assert url.user_id == 1
        event = Event.get_by_id(1)
        assert event.url_id == 1

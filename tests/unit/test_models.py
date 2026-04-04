"""Unit tests for data models — validates schema, constraints, and relationships."""

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    SqliteDatabase,
    TextField,
)

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

# Use in-memory SQLite for unit tests — no PostgreSQL required
test_db = SqliteDatabase(":memory:")


def setup_module():
    """Bind models to test database and create tables."""
    test_db.bind([User, Url, Event])
    test_db.connect()
    test_db.create_tables([User, Url, Event])


def teardown_module():
    """Close test database."""
    test_db.drop_tables([Event, Url, User])
    test_db.close()


class TestUserModel:
    def test_table_name(self):
        assert User._meta.table_name == "users"

    def test_fields_exist(self):
        fields = User._meta.fields
        assert "id" in fields
        assert "username" in fields
        assert "email" in fields
        assert "created_at" in fields

    def test_field_types(self):
        fields = User._meta.fields
        assert isinstance(fields["id"], AutoField)
        assert isinstance(fields["username"], CharField)
        assert isinstance(fields["email"], CharField)
        assert isinstance(fields["created_at"], DateTimeField)

    def test_create_user(self):
        user = User.create(
            username="testuser",
            email="test@example.com",
            created_at="2025-01-01 00:00:00",
        )
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"


class TestUrlModel:
    def test_table_name(self):
        assert Url._meta.table_name == "urls"

    def test_fields_exist(self):
        fields = Url._meta.fields
        assert "id" in fields
        assert "user" in fields  # FK attribute name (column_name="user_id")
        assert "short_code" in fields
        assert "original_url" in fields
        assert "title" in fields
        assert "is_active" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

    def test_field_types(self):
        fields = Url._meta.fields
        assert isinstance(fields["id"], AutoField)
        assert isinstance(fields["user"], ForeignKeyField)
        assert isinstance(fields["short_code"], CharField)
        assert isinstance(fields["original_url"], CharField)
        assert isinstance(fields["title"], CharField)
        assert isinstance(fields["is_active"], BooleanField)
        assert isinstance(fields["created_at"], DateTimeField)
        assert isinstance(fields["updated_at"], DateTimeField)

    def test_short_code_unique(self):
        assert Url._meta.fields["short_code"].unique is True

    def test_short_code_indexed(self):
        assert Url._meta.fields["short_code"].index is True

    def test_is_active_indexed(self):
        assert Url._meta.fields["is_active"].index is True

    def test_is_active_default_true(self):
        assert Url._meta.fields["is_active"].default is True

    def test_foreign_key_to_user(self):
        fk = Url._meta.fields["user"]
        assert fk.rel_model is User
        assert fk.column_name == "user_id"

    def test_create_url(self):
        user = User.create(
            username="urlowner",
            email="owner@example.com",
            created_at="2025-01-01 00:00:00",
        )
        url = Url.create(
            user=user,
            short_code="AbCdEf",
            original_url="https://example.com",
            title="Test URL",
            is_active=True,
            created_at="2025-01-01 00:00:00",
            updated_at="2025-01-01 00:00:00",
        )
        assert url.id is not None
        assert url.short_code == "AbCdEf"
        assert url.user_id == user.id


class TestEventModel:
    def test_table_name(self):
        assert Event._meta.table_name == "events"

    def test_fields_exist(self):
        fields = Event._meta.fields
        assert "id" in fields
        assert "url" in fields  # FK attribute name (column_name="url_id")
        assert "user" in fields  # FK attribute name (column_name="user_id")
        assert "event_type" in fields
        assert "timestamp" in fields
        assert "details" in fields

    def test_field_types(self):
        fields = Event._meta.fields
        assert isinstance(fields["id"], AutoField)
        assert isinstance(fields["url"], ForeignKeyField)
        assert isinstance(fields["user"], ForeignKeyField)
        assert isinstance(fields["event_type"], CharField)
        assert isinstance(fields["timestamp"], DateTimeField)
        assert isinstance(fields["details"], TextField)

    def test_foreign_key_to_url(self):
        fk = Event._meta.fields["url"]
        assert fk.rel_model is Url
        assert fk.column_name == "url_id"

    def test_foreign_key_to_user(self):
        fk = Event._meta.fields["user"]
        assert fk.rel_model is User
        assert fk.column_name == "user_id"

    def test_create_event(self):
        user = User.create(
            username="eventer",
            email="event@example.com",
            created_at="2025-01-01 00:00:00",
        )
        url = Url.create(
            user=user,
            short_code="EvTsT1",
            original_url="https://example.com/event",
            title="Event Test",
            is_active=True,
            created_at="2025-01-01 00:00:00",
            updated_at="2025-01-01 00:00:00",
        )
        event = Event.create(
            url=url,
            user=user,
            event_type="created",
            timestamp="2025-01-01 00:00:00",
            details='{"short_code": "EvTsT1"}',
        )
        assert event.id is not None
        assert event.event_type == "created"
        assert event.url_id == url.id
        assert event.user_id == user.id


class TestReferentialIntegrity:
    def test_user_has_urls_backref(self):
        user = User.create(
            username="backref_user",
            email="backref@example.com",
            created_at="2025-01-01 00:00:00",
        )
        Url.create(
            user=user,
            short_code="BkRf01",
            original_url="https://example.com/backref",
            title="Backref Test",
            is_active=True,
            created_at="2025-01-01 00:00:00",
            updated_at="2025-01-01 00:00:00",
        )
        assert user.urls.count() == 1

    def test_url_has_events_backref(self):
        user = User.create(
            username="evt_backref",
            email="evtbr@example.com",
            created_at="2025-01-01 00:00:00",
        )
        url = Url.create(
            user=user,
            short_code="EvBr01",
            original_url="https://example.com/evtbr",
            title="Event Backref",
            is_active=True,
            created_at="2025-01-01 00:00:00",
            updated_at="2025-01-01 00:00:00",
        )
        Event.create(
            url=url,
            user=user,
            event_type="click",
            timestamp="2025-01-01 00:00:00",
            details="{}",
        )
        assert url.events.count() == 1

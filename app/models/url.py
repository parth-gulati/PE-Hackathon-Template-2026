from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
)

from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    id = AutoField()
    user = ForeignKeyField(User, backref="urls", column_name="user_id")
    short_code = CharField(unique=True, index=True)
    original_url = CharField()
    title = CharField()
    is_active = BooleanField(default=True, index=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        table_name = "urls"

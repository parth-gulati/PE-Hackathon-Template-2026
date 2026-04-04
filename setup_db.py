"""Create database tables for the URL shortener."""

from app import create_app
from app.database import db
from app.models import Event, Url, User

app = create_app()

with app.app_context():
    db.create_tables([User, Url, Event])
    print("Tables created: users, urls, events")

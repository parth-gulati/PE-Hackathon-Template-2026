import csv
import io
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from peewee import chunked
from playhouse.shortcuts import model_to_dict

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["GET", "POST"])
def list_or_create_users():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data:
            return jsonify(error="Request body must be JSON", code="VALIDATION_ERROR"), 400

        missing = [f for f in ("username", "email") if f not in data]
        if missing:
            return jsonify(error=f"Missing required fields: {', '.join(missing)}", code="VALIDATION_ERROR"), 400

        # Validate email format
        email = data["email"]
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            return jsonify(error="Invalid email format", code="VALIDATION_ERROR"), 400

        # Check for duplicate username
        if User.select().where(User.username == data["username"]).exists():
            return jsonify(error="Username already exists", code="DUPLICATE"), 409

        # Check for duplicate email
        if User.select().where(User.email == email).exists():
            return jsonify(error="Email already exists", code="DUPLICATE"), 409

        user = User.create(
            username=data["username"],
            email=email,
            created_at=datetime.now(timezone.utc),
        )
        return jsonify(model_to_dict(user)), 201

    # GET — list users
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    users = User.select().order_by(User.id).paginate(page, per_page)
    return jsonify([model_to_dict(u) for u in users])


@users_bp.route("/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
def get_update_delete_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify(error="User not found", code="NOT_FOUND"), 404

    if request.method == "GET":
        return jsonify(model_to_dict(user))

    if request.method == "PUT":
        data = request.get_json(silent=True)
        if not data:
            return jsonify(error="Request body must be JSON", code="VALIDATION_ERROR"), 400

        if "username" in data:
            existing = User.select().where(
                (User.username == data["username"]) & (User.id != user.id)
            ).exists()
            if existing:
                return jsonify(error="Username already exists", code="DUPLICATE"), 409
            user.username = data["username"]
        if "email" in data:
            existing = User.select().where(
                (User.email == data["email"]) & (User.id != user.id)
            ).exists()
            if existing:
                return jsonify(error="Email already exists", code="DUPLICATE"), 409
            user.email = data["email"]

        user.save()
        return jsonify(model_to_dict(user))

    if request.method == "DELETE":
        # Delete related events and URLs first
        user_urls = Url.select().where(Url.user == user)
        for url in user_urls:
            Event.delete().where(Event.url == url).execute()
        Event.delete().where(Event.user == user).execute()
        Url.delete().where(Url.user == user).execute()
        user.delete_instance()
        return jsonify(message="User deleted"), 200


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_upload_users():
    """Import users from CSV file upload or JSON array."""
    # Handle JSON array
    data = request.get_json(silent=True)
    if data and isinstance(data, list):
        now = datetime.now(timezone.utc)
        rows = [
            {"username": r["username"], "email": r["email"], "created_at": now}
            for r in data
        ]
        with db.atomic():
            for batch in chunked(rows, 100):
                User.insert_many(batch).execute()
        return jsonify(message=f"Imported {len(rows)} users", count=len(rows)), 201

    # Handle CSV file upload
    if "file" in request.files:
        file = request.files["file"]
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        rows = list(reader)

        now = datetime.now(timezone.utc)
        insert_data = [
            {
                "username": r["username"],
                "email": r["email"],
                "created_at": r.get("created_at", now),
            }
            for r in rows
        ]
        with db.atomic():
            for batch in chunked(insert_data, 100):
                User.insert_many(batch).execute()
        return jsonify(message=f"Imported {len(insert_data)} users", count=len(insert_data)), 201

    return jsonify(error="Provide JSON array or CSV file", code="VALIDATION_ERROR"), 400

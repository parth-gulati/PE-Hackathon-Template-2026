from flask import Blueprint, jsonify
from playhouse.shortcuts import model_to_dict

from app.models.user import User

users_bp = Blueprint("users", __name__)


@users_bp.route("/users")
def list_users():
    users = User.select()
    return jsonify([model_to_dict(u) for u in users])


@users_bp.route("/users/<int:user_id>")
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify(error="User not found", code="NOT_FOUND"), 404
    return jsonify(model_to_dict(user))

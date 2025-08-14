from flask import Blueprint, request, jsonify, session
from sqlalchemy import or_

from ..models import db, User
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__)

def _serialize_user(u: User):
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "is_admin": bool(u.is_admin),
        "is_active": bool(u.is_active),
    }

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or request.form or {}
    identifier = (data.get("identifier") or data.get("email") or data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not identifier or not password:
        return jsonify(error="missing_credentials"), 400

    user = User.query.filter(or_(User.username == identifier, User.email == identifier)).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error="invalid_credentials"), 401

    if not user.is_active:
        return jsonify(error="inactive_user"), 403

    session["uid"] = user.id
    return jsonify(user=_serialize_user(user))

@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@auth_bp.get("/me")
def me():
    uid = session.get("uid")
    if not uid:
        return jsonify(user=None)
    user = db.session.get(User, uid)
    return jsonify(user=_serialize_user(user)) if user else (jsonify(user=None), 200)

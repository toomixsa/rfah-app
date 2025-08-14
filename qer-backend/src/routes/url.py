from flask import Blueprint, jsonify

urls_bp = Blueprint("urls", __name__)

@urls_bp.get("/")
def list_urls():
    # Placeholder endpoint
    return jsonify(items=[])

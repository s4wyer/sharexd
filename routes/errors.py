from flask import Blueprint, jsonify

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File exceeds the size limit."}), 413

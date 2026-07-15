import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(413)
def request_entity_too_large(error):
    logger.debug("413 Error triggered: Request Entity Too Large")
    return jsonify({"error": "File exceeds the size limit."}), 413

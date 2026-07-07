import time
from flask import Blueprint, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename
import hmac
import magic

from config import Config
from extensions import limiter, storage
from utils.security import generate_delete_token
from utils.metadata import replace_image_metadata
from utils import generate_filename

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
@limiter.limit("300 per minute")
def upload():
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return jsonify({"error": "Missing Authorization header."}), 401

    expected_token = Config.UPLOAD_TOKEN

    if not expected_token:
        return jsonify({"error": "No secret token. Check your .env."}), 401

    if not hmac.compare_digest(auth_header, expected_token):
        return jsonify({"error": "Invalid Authorization token."}), 401
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided."}), 400           

    uploaded_file = request.files['file']

    if uploaded_file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    file_header = uploaded_file.read(2048)
    # reset the buffer, otherwise the first 2048 bytes will be lost upon saving
    uploaded_file.seek(0)

    mime_type = magic.from_buffer(file_header, mime=True)
    try:
        uploaded_file = replace_image_metadata(uploaded_file, mime_type)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    new_filename = secure_filename(generate_filename.generate_filename(file_header, storage.exists))

    storage.save(uploaded_file, new_filename)

    filename = new_filename

    url = url_for('files.view_file', path=filename)

    timestamp = int(time.time())
    delete_token = generate_delete_token(filename, timestamp)
    delete_url = url_for('upload.delete_file', filename=filename, timestamp=timestamp, token=delete_token)

    return jsonify({"url": url, "delete_url": delete_url})

@upload_bp.route('/delete/<path:filename>/<int:timestamp>/<token>', methods=['DELETE', 'GET', 'POST'])
@limiter.limit("60 per minute")
def delete_file(filename, timestamp, token):
    safe_path = secure_filename(filename)
    expected = generate_delete_token(safe_path, timestamp)

    if not hmac.compare_digest(expected, token):
        return jsonify({"error": "Invalid delete token."}), 403

    if request.method == 'GET':
        return render_template('delete.html', filename=safe_path, deleted=False)

    if not storage.exists(safe_path):
        if request.method == 'POST':
            return render_template('delete.html', filename=safe_path, deleted=False, error="File not found."), 404
        return jsonify({"error": "File not found."}), 404

    storage.delete(safe_path)
    
    if request.method == 'POST':
        return render_template('delete.html', filename=safe_path, deleted=True)
        
    return jsonify({"message": "File deleted."}), 200

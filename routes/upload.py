import time
from flask import Blueprint, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename
import hmac
import magic

from config import Config
from extensions import limiter, storage
from utils.security import generate_delete_token, is_valid_token, get_username_from_token
from utils.metadata import replace_image_metadata
from utils import generate_filename
import json
import io

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
@limiter.limit("300 per minute")
def upload():
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return jsonify({"error": "Missing Authorization header."}), 401

    if not is_valid_token(auth_header):
        return jsonify({"error": "Invalid Authorization token. Check your .env or users file."}), 401
    
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

    username = get_username_from_token(auth_header)
    meta_json = json.dumps({
        "user": username,
        "original_filename": uploaded_file.filename
    }).encode('utf-8')
    meta_file = io.BytesIO(meta_json)
    storage.save(meta_file, f"{new_filename}.meta.json")

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

    is_master_key = Config.MASTER_KEY and Config.MASTER_KEY != "SUPER_SECRET_MASTER_KEY_HERE" and hmac.compare_digest(Config.MASTER_KEY, token)

    if not (hmac.compare_digest(expected, token) or is_master_key):
        return jsonify({"error": "Invalid delete token."}), 403

    if request.method == 'GET':
        return render_template('delete.html', filename=safe_path, deleted=False)

    if not storage.exists(safe_path):
        if request.method == 'POST':
            return render_template('delete.html', filename=safe_path, deleted=False, error="File not found."), 404
        return jsonify({"error": "File not found."}), 404

    storage.delete(safe_path)
    storage.delete(f"{safe_path}.meta.json")
    
    if request.method == 'POST':
        return render_template('delete.html', filename=safe_path, deleted=True)
        
    return jsonify({"message": "File deleted."}), 200

import time
import random
from flask import Blueprint, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename
import hmac
import magic

from config import Config
from extensions import limiter, storage, meta_db
from PIL import Image
from utils.security import generate_delete_token, is_valid_token, get_username_from_token
from utils.metadata import replace_image_metadata
from utils import generate_filename
import json
import io
import libarchive

MAX_ARCHIVE_FILES = 5000
MAX_UNCOMPRESSED_SIZE = 1 * 1024 * 1024 * 1024 # 1 GB

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

    username = get_username_from_token(auth_header)
    timestamp = int(time.time())
    meta_data = {
        "user": username,
        "original_filename": uploaded_file.filename,
        "uploaded_at": timestamp
    }

    if mime_type and mime_type.startswith('image/') and mime_type != 'image/svg+xml':
        try:
            uploaded_file.seek(0)
            with Image.open(uploaded_file) as img:
                meta_data["image_size"] = [img.width, img.height]
            uploaded_file.seek(0)
        except Exception as e:
            print(f"Error getting image size: {e}")
            uploaded_file.seek(0)

    if new_filename.lower().endswith(('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz')):
        try:
            uploaded_file.seek(0)
            archive_contents = []
            total_size = 0
            file_count = 0
            
            with libarchive.seekable_stream_reader(uploaded_file) as archive:
                for entry in archive:
                    file_count += 1
                    if file_count > MAX_ARCHIVE_FILES:
                        raise ValueError("Archive contains too many files (zip bomb protection).")
                    
                    total_size += entry.size
                    if total_size > MAX_UNCOMPRESSED_SIZE:
                        raise ValueError("Archive uncompressed size is too large (zip bomb protection).")
                        
                    archive_contents.append({
                        'name': entry.pathname,
                        'size': entry.size,
                        'is_dir': entry.isdir
                    })
            meta_data["archive_contents"] = archive_contents
            uploaded_file.seek(0)
        except ValueError as e:
            meta_data["archive_error"] = str(e)
            uploaded_file.seek(0)
        except Exception as e:
            meta_data["archive_error"] = "Failed to parse archive."
            print(f"Error caching archive contents: {e}")
            uploaded_file.seek(0)

    storage.save(uploaded_file, new_filename)

    meta_db.set(new_filename, meta_data)

    filename = new_filename

    url = url_for('files.view_file', path=filename)

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
    meta_db.delete(safe_path)
    
    if request.method == 'POST':
        return render_template('delete.html', filename=safe_path, deleted=True)
        
    return jsonify({"message": "File deleted."}), 200

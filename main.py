import os
import mimetypes
from datetime import datetime
import re
import hmac
from pathlib import Path
from utils import generate_filename, get_storage_info
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, url_for
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_UPLOAD_MB", 100)) * 1024 * 1024

Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

@app.template_filter('block_shade')
def block_shade_filter(text):
    return re.sub(r'([█▓▒░▄▀▌▐])', r'<span class="block">\1</span>', text)

@app.route('/')
def index():
    files_count = len(os.listdir(app.config['UPLOAD_FOLDER']))
    storage_size = get_storage_info.pretty_dir_size(app.config['UPLOAD_FOLDER'])
    
    return render_template(
        'index.html',
        version="v1.0.0",
        total_files=files_count,
        storage_used=storage_size,
        abuse_email=os.environ.get("ABUSE_EMAIL", "abuse@yourdomain.com"),
        admin_handle=os.environ.get("ADMIN_HANDLE", "your_handle"),
        github_url=os.environ.get("GITHUB_URL", "https://github.com/yourusername/sharexd")
    )

@app.route('/upload', methods=['POST'])
def upload():
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        return jsonify({"error": "Missing Authorization header."}), 401

    expected_token = os.environ.get("UPLOAD_TOKEN")

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

    # secure_filename should never ever be needed because we generate a new file name
    # but better safe than sorry
    new_filename = secure_filename(generate_filename.generate_filename(file_header))
    safe_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)

    uploaded_file.save(safe_path)

    filename = new_filename

    if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.avif', '.tiff', '.tif')):
        url = f'/view/{filename}'
    else:
        url = f'/{filename}'    

    return jsonify({"url": url })

@app.route('/view/<path:path>')
def view_file(path):
    safe_path = secure_filename(path)
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_path)

    if not os.path.isfile(full_path):
        return jsonify({"error": "File not found."}), 404

    stat = os.stat(full_path)
    file_size = get_storage_info.get_pretty_bytes(stat.st_size)
    mime_type, _ = mimetypes.guess_type(safe_path)
    uploaded_at = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

    response = make_response(render_template(
        'image.html',
        filename=safe_path,
        uploaded_at=uploaded_at,
        file_size=file_size,
        mime_type=mime_type or 'application/octet-stream'
    ))

    # get the stylesheet url so we can whitelist it
    style_url = url_for('static', filename='style.css', _external=True)
    # completely kneecap the browser
    # basically only allow image viewing, downloading, and loading a single stylesheet
    response.headers['Content-Security-Policy'] = f"default-src 'none'; img-src *; style-src {style_url}; sandbox allow-downloads allow-popups"

    return response

@app.route('/<path:path>')
def deliver_file(path):
    safe_path = secure_filename(path)
    # if the user appends ?download, it will be sent as an attachment that will be downloaded
    # instead of viewed
    force_download = 'download' in request.args

    response = make_response(send_from_directory(
        app.config["UPLOAD_FOLDER"],
        safe_path,
        as_attachment=force_download
    ))

    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src *; sandbox allow-downloads"

    if safe_path.endswith(('.html', '.htm', '.xml')):
        response.headers['Content-Type'] = 'text/plain'

    if safe_path.endswith(('.py', '.js')):
        response.headers['Content-Type'] = 'text/plain'

    return response


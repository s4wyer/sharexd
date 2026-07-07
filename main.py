import os
import re
import hmac
import hashlib
import time
from pathlib import Path
from utils import generate_filename
from utils.storage import LocalStorageProvider, S3StorageProvider
from utils.metadata import replace_image_metadata
import magic
from flask import Flask, render_template, request, jsonify, make_response, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

VERSION = "v1.1.3"

def generate_delete_token(filename: str, timestamp: int) -> str:
    secret = os.environ.get("UPLOAD_TOKEN", "").encode()
    msg = f"{filename}:{timestamp}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()

app = Flask(__name__)
# trust reverse proxies to provide correct HTTPS scheme and host headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per minute"],
    storage_uri="memory://"
)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_UPLOAD_MB", 100)) * 1024 * 1024

if os.environ.get("STORAGE_BACKEND") == "s3":
    storage = S3StorageProvider(
        bucket=os.environ.get("S3_BUCKET_NAME"),
        endpoint=os.environ.get("S3_ENDPOINT_URL"),
        access_key=os.environ.get("S3_ACCESS_KEY_ID"),
        secret_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
        region=os.environ.get("S3_REGION", "us-east-1")
    )
else:
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    storage = LocalStorageProvider(folder=app.config['UPLOAD_FOLDER'])

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File exceeds the size limit."}), 413

@app.template_filter('block_shade')
def block_shade_filter(text):
    return re.sub(r'([█▓▒░▄▀▌▐])', r'<span class="block">\1</span>', text)

@app.route('/')
@limiter.limit("100 per minute")
def index():
    stats = storage.get_stats()
    
    return render_template(
        'index.html',
        version=VERSION,
        total_files=stats['total_files'],
        storage_used=stats['storage_used'],
        abuse_email=os.environ.get("ABUSE_EMAIL", "abuse@yourdomain.com"),
        admin_handle=os.environ.get("ADMIN_HANDLE", "your_handle"),
        github_url=os.environ.get("GITHUB_URL", "https://github.com/s4wyer/sharexd")
    )

@app.route('/upload', methods=['POST'])
@limiter.limit("300 per minute")
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

    mime_type = magic.from_buffer(file_header, mime=True)
    uploaded_file = replace_image_metadata(uploaded_file, mime_type)

    # secure_filename should never ever be needed because we generate a new file name
    # but better safe than sorry
    new_filename = secure_filename(generate_filename.generate_filename(file_header, storage.exists))

    storage.save(uploaded_file, new_filename)

    filename = new_filename

    url = url_for('view_file', path=filename)

    timestamp = int(time.time())
    delete_token = generate_delete_token(filename, timestamp)
    delete_url = url_for('delete_file', filename=filename, timestamp=timestamp, token=delete_token)

    return jsonify({"url": url, "delete_url": delete_url})

@app.route('/delete/<path:filename>/<int:timestamp>/<token>', methods=['DELETE', 'GET', 'POST'])
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

@app.route('/view/<path:path>')
@limiter.limit("3000 per minute")
def view_file(path):
    safe_path = secure_filename(path)

    metadata = storage.get_metadata(safe_path)
    if not metadata:
        return jsonify({"error": "File not found."}), 404

    mime_type = metadata['mime_type']
    
    if mime_type.startswith('image/'):
        template_name = 'image.html'
    elif mime_type.startswith('audio/'):
        template_name = 'audio.html'
    elif mime_type.startswith('text/') or mime_type in ['application/json', 'application/xml', 'application/javascript', 'application/x-sh']:
        template_name = 'text.html'
    else:
        template_name = 'viewer.html'

    import secrets
    script_nonce = secrets.token_urlsafe(16)

    kwargs = {
        'filename': safe_path,
        'uploaded_at': metadata['uploaded_at'],
        'file_size': metadata['file_size'],
        'mime_type': mime_type,
        'nonce': script_nonce
    }

    if template_name == 'text.html':
        content_bytes = storage.read(safe_path)
        if content_bytes is None:
            return jsonify({"error": "File not found."}), 404
            
        if len(content_bytes) > 20 * 1024 * 1024:
            content_bytes = content_bytes[:5 * 1024 * 1024] + b'\n... [TRUNCATED: FILE EXCEEDS 20MB LIMIT] ...'
            
        try:
            kwargs['text_content'] = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                kwargs['text_content'] = content_bytes.decode('latin-1')
            except Exception:
                kwargs['text_content'] = "Unable to decode text content."

        kwargs['line_count'] = kwargs['text_content'].count('\n') + 1

    response = make_response(render_template(
        template_name,
        **kwargs
    ))

    # get the stylesheet and font urls so we can whitelist them
    style_url = url_for('static', filename='style.css', _external=True)
    font_url = url_for('static', filename='GeistMono-VariableFont_wght.woff2', _external=True)
    # completely kneecap the browser
    # basically only allow file viewing, downloading, and loading a single stylesheet (plus a nonced inline script for custom players)
    response.headers['Content-Security-Policy'] = f"default-src 'none'; img-src 'self'; media-src 'self'; style-src {style_url} 'unsafe-inline'; script-src 'nonce-{script_nonce}'; font-src {font_url}; sandbox allow-downloads allow-popups allow-scripts allow-same-origin"

    return response

@app.route('/<path:path>')
@limiter.limit("3000 per minute")
def deliver_file(path):
    safe_path = secure_filename(path)
    # if the user appends ?download, it will be sent as an attachment that will be downloaded
    # instead of viewed
    force_download = 'download' in request.args

    response = make_response(storage.stream(safe_path, force_download=force_download))

    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src *; media-src *; sandbox allow-downloads"
    response.headers['Access-Control-Allow-Origin'] = '*'

    if safe_path.endswith(('.html', '.htm', '.xml', '.xhtml', '.mht', '.mhtml')):
        response.headers['Content-Type'] = 'text/plain'

    if safe_path.endswith(('.py', '.js')):
        response.headers['Content-Type'] = 'text/plain'

    return response


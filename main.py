import os
import re
import hmac
from pathlib import Path
from utils import generate_filename
from utils.storage import LocalStorageProvider, S3StorageProvider
from flask import Flask, render_template, request, jsonify, make_response, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

VERSION = "v1.1.0"

app = Flask(__name__)
# trust reverse proxies to provide correct HTTPS scheme and host headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
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
    new_filename = secure_filename(generate_filename.generate_filename(file_header, storage.exists))

    storage.save(uploaded_file, new_filename)

    filename = new_filename

    if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.avif', '.tiff', '.tif')):
        url = f'/view/{filename}'
    else:
        url = f'/{filename}'    

    return jsonify({"url": url })

@app.route('/view/<path:path>')
def view_file(path):
    safe_path = secure_filename(path)

    metadata = storage.get_metadata(safe_path)
    if not metadata:
        return jsonify({"error": "File not found."}), 404

    response = make_response(render_template(
        'image.html',
        filename=safe_path,
        uploaded_at=metadata['uploaded_at'],
        file_size=metadata['file_size'],
        mime_type=metadata['mime_type']
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

    response = make_response(storage.stream(safe_path, force_download=force_download))

    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src *; sandbox allow-downloads"

    if safe_path.endswith(('.html', '.htm', '.xml')):
        response.headers['Content-Type'] = 'text/plain'

    if safe_path.endswith(('.py', '.js')):
        response.headers['Content-Type'] = 'text/plain'

    return response


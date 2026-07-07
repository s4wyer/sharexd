from flask import Blueprint, request, jsonify, make_response, render_template, url_for
from werkzeug.utils import secure_filename
import secrets

from extensions import limiter, storage

files_bp = Blueprint('files', __name__)

@files_bp.route('/view/<path:path>')
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

    script_nonce = secrets.token_urlsafe(16)

    meta_json_bytes = storage.read(f"{safe_path}.meta.json")
    user = "anonymous"
    original_filename = safe_path
    uploaded_at = metadata['uploaded_at']
    if meta_json_bytes:
        import json
        try:
            meta_dict = json.loads(meta_json_bytes.decode('utf-8'))
            user = meta_dict.get('user', 'anonymous')
            original_filename = meta_dict.get('original_filename', safe_path)
            if 'uploaded_at' in meta_dict:
                from datetime import datetime
                uploaded_at = datetime.fromtimestamp(meta_dict['uploaded_at']).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass

    kwargs = {
        'filename': safe_path,
        'original_filename': original_filename,
        'uploaded_at': uploaded_at,
        'file_size': metadata['file_size'],
        'mime_type': mime_type,
        'nonce': script_nonce,
        'uploader': user
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

@files_bp.route('/<path:path>')
@limiter.limit("3000 per minute")
def deliver_file(path):
    safe_path = secure_filename(path)
    # if the user appends ?download, it will be sent as an attachment that will be downloaded
    # instead of viewed
    force_download = 'download' in request.args

    original_filename = safe_path
    if force_download:
        meta_json_bytes = storage.read(f"{safe_path}.meta.json")
        if meta_json_bytes:
            import json
            try:
                meta_dict = json.loads(meta_json_bytes.decode('utf-8'))
                original_filename = meta_dict.get('original_filename', safe_path)
            except Exception:
                pass

    response = make_response(storage.stream(safe_path, force_download=force_download, download_name=original_filename))

    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src *; media-src *; sandbox allow-downloads"
    response.headers['Access-Control-Allow-Origin'] = '*'

    if safe_path.endswith(('.html', '.htm', '.xml', '.xhtml', '.mht', '.mhtml')):
        response.headers['Content-Type'] = 'text/plain'

    if safe_path.endswith(('.py', '.js')):
        response.headers['Content-Type'] = 'text/plain'

    return response

from flask import Blueprint, render_template
from config import Config
from extensions import limiter, storage

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
@limiter.limit("100 per minute")
def index():
    stats = storage.get_stats()
    
    return render_template(
        'index.html',
        version=Config.VERSION,
        total_files=stats['total_files'],
        storage_used=stats['storage_used'],
        abuse_email=Config.ABUSE_EMAIL,
        admin_handle=Config.ADMIN_HANDLE,
        github_url=Config.GITHUB_URL
    )

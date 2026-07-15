import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import limiter
from utils.filters import block_shade_filter

import os
import sys

is_debug = '--debug' in sys.argv or os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('DEBUG') == '1'
logging.basicConfig(level=logging.DEBUG if is_debug else logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    logger.debug("Initializing application.")
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # trust reverse proxies to provide correct HTTPS scheme and host headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # initialize extensions
    limiter.init_app(app)

    # register custom template filters
    app.template_filter('block_shade')(block_shade_filter)

    # register blueprints
    logger.debug("Registering blueprints: errors, home, upload, files, captcha.")
    from routes.errors import errors_bp
    from routes.home import home_bp
    from routes.upload import upload_bp
    from routes.files import files_bp
    from routes.captcha import captcha_bp

    app.register_blueprint(errors_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(captcha_bp)
    
    if app.config.get('TARPIT_ENABLED', True):
        logger.debug("TARPIT_ENABLED is True, registering tarpit blueprint.")
        from routes.tarpit import tarpit_bp
        app.register_blueprint(tarpit_bp)
    else:
        logger.debug("TARPIT_ENABLED is False, skipping tarpit blueprint.")

    logger.debug("Application initialization complete.")
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

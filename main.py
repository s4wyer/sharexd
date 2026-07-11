from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import limiter
from utils.filters import block_shade_filter

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # trust reverse proxies to provide correct HTTPS scheme and host headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # initialize extensions
    limiter.init_app(app)

    # register custom template filters
    app.template_filter('block_shade')(block_shade_filter)

    # register blueprints
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
        from routes.tarpit import tarpit_bp
        app.register_blueprint(tarpit_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

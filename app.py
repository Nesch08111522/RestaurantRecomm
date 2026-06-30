from flask import Flask, render_template
from config import Config
from views.main import main_bp
from views.auth import auth_bp
from views.admin import admin_bp
from views.owner import owner_bp
from context_processors import inject_globals
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    Config.ensure_data_dir()
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(owner_bp, url_prefix='/owner')
    
    @app.context_processor
    def inject():
        return inject_globals()
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app(config_name='development'):
    """Application factory function"""
    app = Flask(__name__)
    
    # Load config
    if config_name == 'production':
        from app.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from app.config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from app.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Initialize OAuth
    from app.oauth import init_oauth
    init_oauth(app)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id)) if user_id else None
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register custom Jinja2 filters
    @app.template_filter('format_vms_date')
    def format_vms_date(timestamp):
        """Format Unix timestamp as VMS-style date: DD-MMM-YYYY"""
        from datetime import datetime
        if not timestamp:
            return ''
        dt = datetime.utcfromtimestamp(timestamp)
        months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        return f"{dt.day:02d}-{months[dt.month - 1]}-{dt.year}"
    
    # Make APP_NAME and DOCROOT available in all templates
    @app.context_processor
    def inject_config():
        return {
            'app_name': app.config.get('APP_NAME', 'BlorfCast'),
            'docroot': app.config.get('DOCROOT', '/Volumes/html/podcast.dev.palodes.com')
        }
    
    # Initialize database tables on app creation
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database initialization warning: {e}")
    
    return app

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()

def create_app(config_name='default'):
    """Application factory pattern"""
    
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def register_blueprints(app):
    """Register application blueprints"""
    
    # Register modular blueprints
    from app.modules.blog import blog_module
    app.register_blueprint(blog_module.blueprint)
    
    from app.modules.auth import auth_module
    app.register_blueprint(auth_module.blueprint, url_prefix='/auth')
    
    from app.modules.dashboard import dashboard_module
    app.register_blueprint(dashboard_module.blueprint, url_prefix='/dashboard')
    
    from app.modules.media import media_module
    app.register_blueprint(media_module.blueprint, url_prefix='/media')

def register_context_processors(app):
    """Register template context processors"""
    
    @app.context_processor
    def inject_global_vars():
        from app.models import Setting, Category, Post
        from flask_login import current_user
        
        # Get blog settings
        settings = {}
        for setting in Setting.query.all():
            settings[setting.key] = setting.value
        
        # Get active categories for navigation
        categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).limit(10).all()
        
        # Helper functions for templates
        def get_categories():
            return categories
            
        def get_recent_posts(limit=5):
            return Post.query.filter_by(status='published').order_by(
                Post.published_at.desc()
            ).limit(limit).all()
        
        return {
            'blog_settings': settings,
            'get_categories': get_categories,
            'get_recent_posts': get_recent_posts,
            'google_analytics_id': app.config.get('GOOGLE_ANALYTICS_ID'),
        }

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        try:
            from flask import render_template
            return render_template('errors/404.html'), 404
        except:
            return '<h1>404 - Page Not Found</h1><p><a href="/">Go Home</a></p>', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        try:
            from flask import render_template
            db.session.rollback()
            # Log the actual error for debugging
            app.logger.error(f'Server Error: {error}', exc_info=True)
            return render_template('errors/500.html'), 500
        except Exception as e:
            # Fallback if template rendering fails
            app.logger.error(f'Error handler failed: {e}', exc_info=True)
            return '<h1>500 - Internal Server Error</h1><p>Something went wrong. <a href="/">Go Home</a></p>', 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        try:
            from flask import render_template
            return render_template('errors/403.html'), 403
        except:
            return '<h1>403 - Access Forbidden</h1><p><a href="/">Go Home</a></p>', 403
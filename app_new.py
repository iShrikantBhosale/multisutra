#!/usr/bin/env python3
"""
Simple Blog CMS - Modular Design
Run script for the Flask application
"""

import os
import sys
from datetime import datetime
from flask import Flask

def create_flask_app():
    """Create and configure the Flask application"""
    try:
        print("🚀 Starting Simple Blog CMS...")
        print(f"Python version: {sys.version}")
        
        # Determine environment
        env = os.environ.get('FLASK_ENV', 'production')
        print(f"Environment: {env}")
        
        # Check database configuration
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            print(f"Database URL configured: Yes")
        else:
            print(f"Database URL configured: No")
        
        print("Creating Flask app...")
        
        # Import app factory
        from app import create_app
        app = create_app()
        
        print("✓ Flask app created successfully")
        
        # Initialize database
        initialize_database(app)
        
        print("🎉 App initialization completed successfully!")
        
        if env == 'production':
            print("Production mode: Use gunicorn to run the app")
            print("Example: gunicorn --bind 0.0.0.0:8000 run:app")
        
        return app
        
    except Exception as e:
        print(f"❌ Error creating app: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal Flask app to prevent crashes
        app = Flask(__name__)
        
        @app.route('/')
        def error_page():
            return f'<h1>Application Error</h1><p>Failed to start: {e}</p><p><a href="/setup">Try Setup</a></p>', 500
        
        return app

def initialize_database(app):
    """Initialize database tables and create default data"""
    try:
        with app.app_context():
            print("Testing database connection...")
            
            from app import db
            from app.models import User, Category, Setting, Post
            
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            print("✓ Database connection successful")
            
            # Create tables
            db.create_all()
            print("✓ Database tables created")
            
            # Check if we have any users
            user_count = User.query.count()
            if user_count == 0:
                print("Creating default admin user...")
                
                # Create admin user
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    first_name='Admin',
                    last_name='User',
                    role='admin',
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                admin.set_password('admin123')  # Change this in production!
                
                db.session.add(admin)
                db.session.commit()
                print("✓ Admin user created (username: admin, password: admin123)")
            
            # Create default category
            if Category.query.count() == 0:
                category = Category(
                    name='General',
                    slug='general',
                    description='General blog posts',
                    color='#007bff',
                    sort_order=0,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(category)
                db.session.commit()
                print("✓ Default category created")
            
            # Create default settings
            default_settings = {
                'blog_title': 'My Blog',
                'blog_description': 'A simple blog powered by Flask',
                'posts_per_page': '6',
                'enable_comments': 'true',
                'moderate_comments': 'true'
            }
            
            for key, value in default_settings.items():
                if not Setting.query.filter_by(key=key).first():
                    setting = Setting(key=key, value=value)
                    db.session.add(setting)
            
            db.session.commit()
            print("✓ Default settings created")
            
            print("✓ Database initialization completed")
            
    except Exception as e:
        print(f"⚠️ Database initialization issue: {e}")
        import traceback
        traceback.print_exc()

# Create the Flask app instance
app = create_flask_app()

if __name__ == '__main__':
    # Development server
    app.run(host='127.0.0.1', port=5000, debug=True)
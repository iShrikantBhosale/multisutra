#!/usr/bin/env python3
"""
Application entry point for production deployment.
This file creates and configures the Flask application instance.
"""

import os
import sys
import traceback
from app import create_app, db

print(f"🚀 Starting MultiSutra CMS...")
print(f"Python version: {sys.version}")
print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
print(f"Database URL configured: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")

try:
    # Create Flask application instance
    print("Creating Flask app...")
    app = create_app(os.environ.get('FLASK_ENV', 'production'))
    print("✓ Flask app created successfully")
    
    # Test database connection and initialize if needed
    print("Testing database connection...")
    with app.app_context():
        try:
            # Test basic connection
            db.engine.connect()
            print("✓ Database connection successful")
            
            # Try to query tenants table to see if it exists
            from app.models.tenant import Tenant
            tenant_count = Tenant.query.count()
            print(f"✓ Found {tenant_count} tenants in database")
            
            # If no tenants exist, create a default one
            if tenant_count == 0:
                print("Creating default tenant...")
                from datetime import datetime
                tenant = Tenant(
                    name='MultiSutra Blog',
                    subdomain='main',
                    domain=os.environ.get('MAIN_DOMAIN', 'multisutra.onrender.com'),
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(tenant)
                db.session.commit()
                print("✓ Default tenant created")
                
        except Exception as db_error:
            print(f"⚠️  Database issue detected: {db_error}")
            print("Attempting to initialize database...")
            
            # Try to create all tables
            db.create_all()
            print("✓ Database tables created")
            
            # Create default tenant
            from app.models.tenant import Tenant
            from datetime import datetime
            tenant = Tenant(
                name='MultiSutra Blog',
                subdomain='main',
                domain=os.environ.get('MAIN_DOMAIN', 'multisutra.onrender.com'),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(tenant)
            db.session.commit()
            print("✓ Database initialized with default tenant")
        
    print("🎉 App initialization completed successfully!")
    
except Exception as e:
    print(f"❌ Critical error during app initialization: {e}")
    traceback.print_exc()
    
    # Create a minimal error app that can at least respond
    print("Creating minimal error response app...")
    from flask import Flask, jsonify, render_template_string
    app = Flask(__name__)
    
    error_html = """
    <!DOCTYPE html>
    <html>
    <head><title>MultiSutra CMS - Initialization Error</title></head>
    <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
        <h1>🚧 MultiSutra CMS - Setup Required</h1>
        <p><strong>Error:</strong> {{ error_message }}</p>
        <p>The application encountered an initialization error. This usually means:</p>
        <ul>
            <li>Database is not accessible</li>
            <li>Required environment variables are missing</li>
            <li>First-time setup is needed</li>
        </ul>
        <p><a href="/debug">View Debug Information</a></p>
    </body>
    </html>
    """
    
    @app.route('/')
    def error_info():
        return render_template_string(error_html, error_message=str(e))
    
    @app.route('/debug')
    def debug_info():
        return jsonify({
            'error': str(e),
            'environment': os.environ.get('FLASK_ENV', 'unknown'),
            'database_url': 'CONFIGURED' if os.environ.get('DATABASE_URL') else 'MISSING',
            'port': os.environ.get('PORT', 'not set'),
            'secret_key': 'CONFIGURED' if os.environ.get('SECRET_KEY') else 'MISSING'
        })
    
    @app.route('/env')
    def env_info():
        """Show environment variables (safe ones only)"""
        safe_env = {}
        for key, value in os.environ.items():
            if not any(secret in key.upper() for secret in ['SECRET', 'PASSWORD', 'TOKEN', 'KEY']):
                safe_env[key] = value[:50] + '...' if len(value) > 50 else value
        return jsonify({
            'environment_variables': safe_env,
            'python_version': sys.version,
            'working_directory': os.getcwd()
        })
    
    @app.route('/test-db')
    def test_database():
        """Test database connectivity"""
        try:
            db_url = os.environ.get('DATABASE_URL', 'Not configured')
            return jsonify({
                'database_url_configured': bool(os.environ.get('DATABASE_URL')),
                'database_type': 'PostgreSQL' if 'postgresql' in db_url.lower() else 'SQLite' if 'sqlite' in db_url.lower() else 'Unknown',
                'status': 'Database connection test route (basic app mode)'
            })
        except Exception as db_e:
            return jsonify({
                'error': f'Database test failed: {str(db_e)}',
                'database_url_configured': bool(os.environ.get('DATABASE_URL'))
            })
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'error', 'message': 'App failed to initialize properly'})

# CLI commands for database initialization
@app.cli.command()
def init_db():
    """Initialize database with tables"""
    with app.app_context():
        db.create_all()
        print("Database initialized!")

@app.cli.command()
def create_super_admin():
    """Create a super admin user"""
    from app.models.tenant import Tenant
    from app.models.user import User
    
    with app.app_context():
        email = input("Enter super admin email: ").strip()
        password = input("Enter password: ").strip()
        name = input("Enter name: ").strip()
        
        # Create default tenant if not exists
        tenant = Tenant.query.filter_by(subdomain='admin').first()
        if not tenant:
            tenant = Tenant(
                name='Admin',
                subdomain='admin',
                domain='localhost',
                is_active=True
            )
            db.session.add(tenant)
            db.session.commit()
        
        # Create super admin user
        user = User(
            email=email,
            name=name,
            tenant_id=tenant.id,
            role='admin',
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"Super admin created: {email}")

if __name__ == '__main__':
    # Only run in development mode when called directly
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
    else:
        print("Production mode: Use gunicorn to run the app")
        print("Example: gunicorn --bind 0.0.0.0:8000 run:app")
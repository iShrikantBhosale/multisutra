#!/usr/bin/env python3
"""
Application entry point for production deployment.
This file creates and configures the Flask application instance.
"""

import os
from app import create_app, db

# Create Flask application instance
app = create_app(os.environ.get('FLASK_ENV', 'production'))

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
#!/usr/bin/env python3
"""
Database initialization script for production deployment.
This helps set up the database when the app first starts.
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

def create_minimal_app():
    """Create minimal app for database operations"""
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'temp-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///temp.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    return app

def init_database():
    """Initialize database with basic tables"""
    print("Initializing database...")
    
    app = create_minimal_app()
    db = SQLAlchemy(app)
    
    # Define minimal models for database creation
    class Tenant(db.Model):
        __tablename__ = 'tenants'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        subdomain = db.Column(db.String(50), unique=True, nullable=False)
        domain = db.Column(db.String(200), nullable=False)
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    class User(db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), nullable=False)
        username = db.Column(db.String(80), nullable=False)
        first_name = db.Column(db.String(50))
        last_name = db.Column(db.String(50))
        password_hash = db.Column(db.String(200))
        tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
        role = db.Column(db.String(20), default='editor')
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    with app.app_context():
        try:
            # Test database connection
            db.engine.connect()
            print("✓ Database connection successful")
            
            # Create tables
            db.create_all()
            print("✓ Database tables created")
            
            # Create default tenant if it doesn't exist
            tenant = Tenant.query.filter_by(subdomain='main').first()
            if not tenant:
                tenant = Tenant(
                    name='MultiSutra Blog',
                    subdomain='main',
                    domain='multisutra.onrender.com'
                )
                db.session.add(tenant)
                db.session.commit()
                print("✓ Default tenant created")
            else:
                print("✓ Default tenant already exists")
                
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
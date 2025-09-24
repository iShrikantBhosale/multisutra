"""
Auth Module - Handles authentication, user management, and session management
Modular design inspired by Astro's approach
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

from app import db
from app.models import User

class AuthModule:
    """Auth module with clean separation of concerns"""
    
    def __init__(self):
        self.blueprint = Blueprint('auth', __name__)
        self._register_routes()
    
    def _register_routes(self):
        """Register all auth routes"""
        self.blueprint.add_url_rule('/login', 'login', self.login, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/register', 'register', self.register, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/logout', 'logout', self.logout)
        self.blueprint.add_url_rule('/profile', 'profile', self.profile, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/change-password', 'change_password', self.change_password, methods=['GET', 'POST'])
    
    def login(self):
        """Handle user login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        if request.method == 'POST':
            data = self._get_form_data()
            result = self._authenticate_user(data['email'], data['password'], data.get('remember', False))
            
            if result['success']:
                return redirect(request.args.get('next') or url_for('dashboard.index'))
            else:
                flash(result['message'], 'error')
        
        return render_template('components/auth/login.html')
    
    def register(self):
        """Handle user registration"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        if request.method == 'POST':
            data = self._get_form_data()
            result = self._create_user(data)
            
            if result['success']:
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash(result['message'], 'error')
        
        return render_template('components/auth/register.html')
    
    def logout(self):
        """Handle user logout"""
        logout_user()
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('blog.index'))
    
    @login_required
    def profile(self):
        """Handle user profile management"""
        if request.method == 'POST':
            data = self._get_form_data()
            result = self._update_profile(current_user, data)
            
            if result['success']:
                flash('Profile updated successfully!', 'success')
            else:
                flash(result['message'], 'error')
            
            return redirect(url_for('auth.profile'))
        
        return render_template('components/auth/profile.html', user=current_user)
    
    @login_required
    def change_password(self):
        """Handle password change"""
        if request.method == 'POST':
            data = self._get_form_data()
            result = self._change_password(current_user, data)
            
            if result['success']:
                flash('Password changed successfully!', 'success')
                return redirect(url_for('auth.profile'))
            else:
                flash(result['message'], 'error')
        
        return render_template('components/auth/change_password.html')
    
    def _get_form_data(self):
        """Extract and clean form data"""
        return {
            'email': request.form.get('email', '').strip().lower(),
            'password': request.form.get('password', ''),
            'username': request.form.get('username', '').strip(),
            'first_name': request.form.get('first_name', '').strip(),
            'last_name': request.form.get('last_name', '').strip(),
            'bio': request.form.get('bio', '').strip(),
            'website_url': request.form.get('website_url', '').strip(),
            'current_password': request.form.get('current_password', ''),
            'new_password': request.form.get('new_password', ''),
            'confirm_password': request.form.get('confirm_password', ''),
            'remember': bool(request.form.get('remember'))
        }
    
    def _authenticate_user(self, email, password, remember=False):
        """Authenticate user credentials"""
        if not email or not password:
            return {'success': False, 'message': 'Please provide both email and password.'}
        
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return {'success': True, 'user': user}
        
        return {'success': False, 'message': 'Invalid email or password.'}
    
    def _create_user(self, data):
        """Create new user account"""
        # Validate required fields
        required_fields = ['email', 'password', 'username', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return {'success': False, 'message': f'{field.replace("_", " ").title()} is required.'}
        
        # Validate email format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
            return {'success': False, 'message': 'Please enter a valid email address.'}
        
        # Validate password length
        if len(data['password']) < 8:
            return {'success': False, 'message': 'Password must be at least 8 characters long.'}
        
        # Check password confirmation
        if data['password'] != data.get('confirm_password'):
            return {'success': False, 'message': 'Passwords do not match.'}
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_]+$', data['username']):
            return {'success': False, 'message': 'Username can only contain letters, numbers, and underscores.'}
        
        # Check if email or username already exists
        if User.query.filter_by(email=data['email']).first():
            return {'success': False, 'message': 'Email address already registered.'}
        
        if User.query.filter_by(username=data['username']).first():
            return {'success': False, 'message': 'Username already taken.'}
        
        try:
            # Create user
            user = User(
                email=data['email'],
                username=data['username'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                role='author'  # Default role for new users
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            return {'success': True, 'user': user}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': 'An error occurred during registration. Please try again.'}
    
    def _update_profile(self, user, data):
        """Update user profile"""
        try:
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.bio = data.get('bio', user.bio)
            
            # Validate and set website URL
            website_url = data.get('website_url', '')
            if website_url and not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url
            user.website_url = website_url
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': 'An error occurred updating your profile.'}
    
    def _change_password(self, user, data):
        """Change user password"""
        if not data.get('current_password'):
            return {'success': False, 'message': 'Current password is required.'}
        
        if not user.check_password(data['current_password']):
            return {'success': False, 'message': 'Current password is incorrect.'}
        
        if len(data.get('new_password', '')) < 8:
            return {'success': False, 'message': 'New password must be at least 8 characters long.'}
        
        if data['new_password'] != data.get('confirm_password'):
            return {'success': False, 'message': 'New passwords do not match.'}
        
        try:
            user.set_password(data['new_password'])
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': 'An error occurred changing your password.'}

# Create module instance
auth_module = AuthModule()
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.models import User, Tenant
from app.utils.tenant import get_current_tenant, tenant_required
from app import db
import secrets
from datetime import datetime, timedelta

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
@tenant_required
def login():
    """User login"""
    tenant = get_current_tenant()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('auth/login.html', tenant=tenant)
        
        # Find user in current tenant
        user = User.for_tenant(tenant.id).filter_by(email=email, is_active=True).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', tenant=tenant)

@bp.route('/register', methods=['GET', 'POST'])
@tenant_required
def register():
    """User registration"""
    tenant = get_current_tenant()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Check if registration is allowed
    # For now, we'll allow registration but you might want to restrict this
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not email:
            errors.append('Email is required.')
        elif '@' not in email:
            errors.append('Please provide a valid email address.')
        
        if not username:
            errors.append('Username is required.')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Check if email already exists in this tenant
        if email and User.for_tenant(tenant.id).filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        
        # Check if username already exists in this tenant
        if username and User.for_tenant(tenant.id).filter_by(username=username).first():
            errors.append('This username is already taken.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', tenant=tenant)
        
        # Create new user
        user = User(
            tenant_id=tenant.id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role='editor'  # Default role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', tenant=tenant)

@bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
@tenant_required
def profile():
    """User profile management"""
    tenant = get_current_tenant()
    user = current_user
    
    if request.method == 'POST':
        # Update profile information
        user.first_name = request.form.get('first_name', '').strip()
        user.last_name = request.form.get('last_name', '').strip()
        user.bio = request.form.get('bio', '').strip()
        user.website_url = request.form.get('website_url', '').strip()
        
        # Validate website URL
        if user.website_url and not user.website_url.startswith(('http://', 'https://')):
            user.website_url = 'https://' + user.website_url
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', tenant=tenant, user=user)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@tenant_required
def change_password():
    """Change user password"""
    tenant = get_current_tenant()
    user = current_user
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
        elif len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'error')
        else:
            user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', tenant=tenant)

@bp.route('/forgot-password', methods=['GET', 'POST'])
@tenant_required
def forgot_password():
    """Forgot password - request reset"""
    tenant = get_current_tenant()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please provide your email address.', 'error')
            return render_template('auth/forgot_password.html', tenant=tenant)
        
        user = User.for_tenant(tenant.id).filter_by(email=email, is_active=True).first()
        
        if user:
            # Generate password reset token
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # In a real application, you would send an email here
            # For now, we'll just show a message
            flash('Password reset instructions have been sent to your email.', 'info')
        else:
            # Don't reveal if email exists or not for security
            flash('If an account with that email exists, password reset instructions have been sent.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', tenant=tenant)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@tenant_required
def reset_password(token):
    """Reset password with token"""
    tenant = get_current_tenant()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Find user by token
    user = User.for_tenant(tenant.id).filter_by(password_reset_token=token).first()
    
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        flash('Invalid or expired password reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
        elif password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            user.set_password(password)
            user.password_reset_token = None
            user.password_reset_expires = None
            db.session.commit()
            
            flash('Password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', tenant=tenant, token=token)
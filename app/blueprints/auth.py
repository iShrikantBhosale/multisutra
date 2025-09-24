from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.models import User, Tenant
from app.forms import LoginForm, RegisterForm, ProfileForm, ChangePasswordForm, ForgotPasswordForm, ResetPasswordForm
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
    form = LoginForm()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if form.validate_on_submit():
        username_or_email = form.username.data.strip().lower()
        password = form.password.data
        remember = form.remember_me.data
        
        # Find user by email or username in current tenant
        user = User.for_tenant(tenant.id).filter(
            (User.email == username_or_email) | 
            (User.username == username_or_email)
        ).filter_by(is_active=True).first()
        
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
            flash('Invalid username/email or password.', 'error')
    
    return render_template('auth/login.html', tenant=tenant, form=form)

@bp.route('/register', methods=['GET', 'POST'])
@tenant_required
def register():
    """User registration"""
    tenant = get_current_tenant()
    form = RegisterForm()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Check if registration is allowed
    # For now, we'll allow registration but you might want to restrict this
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            tenant_id=tenant.id,
            email=form.email.data.lower(),
            username=form.username.data.strip(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            role='editor'  # Default role
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', tenant=tenant, form=form)

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
    form = ProfileForm(obj=user)
    
    if form.validate_on_submit():
        # Update profile information
        form.populate_obj(user)
        
        # Validate website URL
        if user.website_url and not user.website_url.startswith(('http://', 'https://')):
            user.website_url = 'https://' + user.website_url
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', tenant=tenant, user=user, form=form)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@tenant_required
def change_password():
    """Change user password"""
    tenant = get_current_tenant()
    user = current_user
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Validation
        if not user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
        else:
            user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', tenant=tenant, form=form)

@bp.route('/forgot-password', methods=['GET', 'POST'])
@tenant_required
def forgot_password():
    """Forgot password - request reset"""
    tenant = get_current_tenant()
    form = ForgotPasswordForm()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if form.validate_on_submit():
        email = form.email.data.lower()
        
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
    
    return render_template('auth/forgot_password.html', tenant=tenant, form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@tenant_required
def reset_password(token):
    """Reset password with token"""
    tenant = get_current_tenant()
    form = ResetPasswordForm()
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Find user by token
    user = User.for_tenant(tenant.id).filter_by(password_reset_token=token).first()
    
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        flash('Invalid or expired password reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        
        flash('Password has been reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', tenant=tenant, token=token, form=form)
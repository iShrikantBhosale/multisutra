"""
WTForms form classes for the application
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, EmailField, URLField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError
from wtforms.widgets import TextArea
from app.models import User
from app.utils.tenant import get_current_tenant

class LoginForm(FlaskForm):
    """Login form"""
    username = StringField('Username', validators=[DataRequired()], render_kw={'placeholder': 'Username or Email'})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    remember_me = BooleanField('Remember me')

class RegisterForm(FlaskForm):
    """Registration form"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=1, max=50)], render_kw={'placeholder': 'First Name'})
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=1, max=50)], render_kw={'placeholder': 'Last Name'})
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)], render_kw={'placeholder': 'Username'})
    email = EmailField('Email', validators=[DataRequired(), Email()], render_kw={'placeholder': 'your@email.com'})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)], render_kw={'placeholder': 'Password'})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')], render_kw={'placeholder': 'Confirm Password'})

    def validate_username(self, username):
        """Check if username already exists in current tenant"""
        tenant = get_current_tenant()
        if tenant:
            user = User.for_tenant(tenant.id).filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, email):
        """Check if email already exists in current tenant"""
        tenant = get_current_tenant()
        if tenant:
            user = User.for_tenant(tenant.id).filter_by(email=email.data.lower()).first()
            if user:
                raise ValidationError('Email already registered. Please use a different email or login.')

class ProfileForm(FlaskForm):
    """User profile update form"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=1, max=50)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)], render_kw={'rows': 4, 'placeholder': 'Tell us about yourself...'})
    website_url = URLField('Website URL', validators=[Optional()], render_kw={'placeholder': 'https://your-website.com'})

class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[DataRequired()], render_kw={'placeholder': 'Current Password'})
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)], render_kw={'placeholder': 'New Password'})
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')], render_kw={'placeholder': 'Confirm New Password'})

class ForgotPasswordForm(FlaskForm):
    """Forgot password form"""
    email = EmailField('Email', validators=[DataRequired(), Email()], render_kw={'placeholder': 'Enter your email address'})

class ResetPasswordForm(FlaskForm):
    """Reset password form"""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)], render_kw={'placeholder': 'New Password'})
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')], render_kw={'placeholder': 'Confirm New Password'})
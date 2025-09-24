from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.utils.tenant import TenantMixin

class User(UserMixin, TenantMixin, db.Model):
    """User model with multi-tenant support"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    
    # Basic user information
    email = db.Column(db.String(120), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    
    # Role and permissions
    role = db.Column(db.String(20), default='editor', index=True)  # admin, editor
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), nullable=True)
    
    # Password reset
    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    media_files = db.relationship('MediaFile', backref='uploaded_by_user', lazy='dynamic')
    
    # Unique constraint for email per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'email', name='_tenant_email_uc'),
        db.UniqueConstraint('tenant_id', 'username', name='_tenant_username_uc'),
    )
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username
    
    @property
    def display_name(self):
        """Get display name"""
        return self.full_name or self.username
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_editor(self):
        """Check if user is editor or admin"""
        return self.role in ['admin', 'editor']
    
    def can_edit_post(self, post):
        """Check if user can edit a specific post"""
        if self.is_admin():
            return True
        return post.author_id == self.id
    
    def can_delete_post(self, post):
        """Check if user can delete a specific post"""
        if self.is_admin():
            return True
        return post.author_id == self.id
    
    def get_avatar_url(self, size=80):
        """Get avatar URL with fallback to Gravatar"""
        if self.avatar_url:
            return self.avatar_url
        
        # Fallback to Gravatar
        import hashlib
        email_hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=identicon"
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'bio': self.bio,
            'avatar_url': self.get_avatar_url(),
            'website_url': self.website_url,
            'role': self.role,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
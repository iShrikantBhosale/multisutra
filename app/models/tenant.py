from datetime import datetime
from app import db
from sqlalchemy import event

class Tenant(db.Model):
    """Tenant model for multi-tenancy"""
    __tablename__ = 'tenants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False, index=True)
    domain = db.Column(db.String(100), nullable=True)  # Custom domain support
    
    # Tenant settings
    title = db.Column(db.String(200), default='My Blog')
    description = db.Column(db.Text, default='Welcome to my blog')
    logo_url = db.Column(db.String(255), nullable=True)
    favicon_url = db.Column(db.String(255), nullable=True)
    
    # Theme and customization
    theme = db.Column(db.String(50), default='default')
    custom_css = db.Column(db.Text, nullable=True)
    custom_js = db.Column(db.Text, nullable=True)
    
    # SEO settings
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.String(255), nullable=True)
    google_analytics_id = db.Column(db.String(50), nullable=True)
    google_adsense_id = db.Column(db.String(50), nullable=True)
    
    # Social media
    facebook_url = db.Column(db.String(255), nullable=True)
    twitter_url = db.Column(db.String(255), nullable=True)
    instagram_url = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    
    # Status and timestamps
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    posts = db.relationship('Post', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    media_files = db.relationship('MediaFile', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('Setting', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Tenant {self.subdomain}>'
    
    @property
    def full_domain(self):
        """Get the full domain for this tenant"""
        if self.domain:
            return self.domain
        from flask import current_app
        main_domain = current_app.config.get('MAIN_DOMAIN', 'multisutra.com')
        return f"{self.subdomain}.{main_domain}"
    
    @property
    def url(self):
        """Get the full URL for this tenant"""
        return f"https://{self.full_domain}"
    
    def get_setting(self, key, default=None):
        """Get a setting value for this tenant"""
        setting = Setting.query.filter_by(tenant_id=self.id, key=key).first()
        return setting.value if setting else default
    
    def set_setting(self, key, value):
        """Set a setting value for this tenant"""
        setting = Setting.query.filter_by(tenant_id=self.id, key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(tenant_id=self.id, key=key, value=value)
            db.session.add(setting)
        return setting
    
    def to_dict(self):
        """Convert tenant to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'subdomain': self.subdomain,
            'domain': self.domain,
            'title': self.title,
            'description': self.description,
            'theme': self.theme,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'url': self.url,
            'full_domain': self.full_domain
        }

# Import models to establish relationships
from app.models.user import User
from app.models.post import Post
from app.models.category import Category
from app.models.tag import Tag
from app.models.media import MediaFile
from app.models.setting import Setting
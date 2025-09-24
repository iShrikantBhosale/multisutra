from datetime import datetime
from app import db
from app.utils.tenant import TenantMixin

class Setting(TenantMixin, db.Model):
    """Settings model for tenant-specific configurations"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    
    # Setting data
    key = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, json
    
    # Metadata
    description = db.Column(db.String(255), nullable=True)
    is_public = db.Column(db.Boolean, default=False)  # Can be accessed from templates
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint for key per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'key', name='_tenant_setting_key_uc'),
    )
    
    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'
    
    @property
    def parsed_value(self):
        """Get value parsed according to data_type"""
        if not self.value:
            return None
            
        if self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return 0
        elif self.data_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except (ValueError, TypeError):
                return {}
        else:
            return self.value
    
    def set_value(self, value):
        """Set value with automatic type conversion"""
        if isinstance(value, bool):
            self.data_type = 'boolean'
            self.value = str(value).lower()
        elif isinstance(value, int):
            self.data_type = 'integer'
            self.value = str(value)
        elif isinstance(value, (dict, list)):
            self.data_type = 'json'
            import json
            self.value = json.dumps(value)
        else:
            self.data_type = 'string'
            self.value = str(value) if value is not None else None
    
    def to_dict(self):
        """Convert setting to dictionary"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'parsed_value': self.parsed_value,
            'data_type': self.data_type,
            'description': self.description,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Comment(TenantMixin, db.Model):
    """Comment model for blog posts"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True, index=True)
    
    # Author information (can be guest or registered user)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    author_name = db.Column(db.String(100), nullable=False)
    author_email = db.Column(db.String(120), nullable=False)
    author_website = db.Column(db.String(255), nullable=True)
    author_ip = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    
    # Content
    content = db.Column(db.Text, nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, spam, trash
    is_approved = db.Column(db.Boolean, default=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = db.relationship('User', backref='comments')
    replies = db.relationship('Comment', backref=db.backref('parent_comment', remote_side=[id]), lazy='dynamic')
    
    def __repr__(self):
        return f'<Comment by {self.author_name}>'
    
    @property
    def is_guest(self):
        """Check if comment is from a guest user"""
        return self.user_id is None
    
    @property
    def author_display_name(self):
        """Get author display name"""
        if self.author:
            return self.author.display_name
        return self.author_name
    
    @property
    def avatar_url(self):
        """Get author avatar URL"""
        if self.author:
            return self.author.get_avatar_url(40)
        
        # Fallback to Gravatar for guest users
        import hashlib
        email_hash = hashlib.md5(self.author_email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s=40&d=identicon"
    
    def approve(self):
        """Approve the comment"""
        self.status = 'approved'
        self.is_approved = True
    
    def mark_as_spam(self):
        """Mark comment as spam"""
        self.status = 'spam'
        self.is_approved = False
    
    def trash(self):
        """Move comment to trash"""
        self.status = 'trash'
        self.is_approved = False
    
    def to_dict(self):
        """Convert comment to dictionary"""
        return {
            'id': self.id,
            'content': self.content,
            'author_name': self.author_name,
            'author_display_name': self.author_display_name,
            'author_website': self.author_website,
            'avatar_url': self.avatar_url,
            'is_guest': self.is_guest,
            'status': self.status,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'parent_id': self.parent_id,
            'reply_count': self.replies.count()
        }
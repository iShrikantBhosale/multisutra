from datetime import datetime
from app import db
from app.utils.tenant import TenantMixin
from sqlalchemy import event

class Category(TenantMixin, db.Model):
    """Blog category model"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True, index=True)
    
    # Basic information
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # SEO
    meta_title = db.Column(db.String(200), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    
    # Display
    color = db.Column(db.String(7), nullable=True)  # Hex color
    icon = db.Column(db.String(50), nullable=True)  # Icon class or URL
    sort_order = db.Column(db.Integer, default=0, index=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='category', lazy='dynamic')
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    
    # Unique constraint for slug per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'slug', name='_tenant_category_slug_uc'),
    )
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    @property
    def post_count(self):
        """Get number of published posts in this category"""
        return self.posts.filter_by(status='published').count()
    
    @property
    def url(self):
        """Get category URL"""
        from app.utils.tenant import get_current_tenant
        tenant = get_current_tenant()
        if tenant:
            return f"https://{tenant.full_domain}/category/{self.slug}"
        return f"/category/{self.slug}"
    
    @property
    def breadcrumb(self):
        """Get breadcrumb trail"""
        trail = []
        current = self
        while current:
            trail.append(current)
            current = current.parent
        return list(reversed(trail))
    
    def get_all_children(self):
        """Get all descendant categories"""
        children = []
        for child in self.children:
            children.append(child)
            children.extend(child.get_all_children())
        return children
    
    def to_dict(self):
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'post_count': self.post_count,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'url': self.url,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Tag(TenantMixin, db.Model):
    """Blog tag model"""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    
    # Basic information
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Display
    color = db.Column(db.String(7), nullable=True)  # Hex color
    
    # Stats
    use_count = db.Column(db.Integer, default=0, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint for slug per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'slug', name='_tenant_tag_slug_uc'),
    )
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
    @property
    def post_count(self):
        """Get number of published posts with this tag"""
        from app.models.post import post_tags
        from app.models.post import Post
        return db.session.query(Post).join(post_tags).filter(
            post_tags.c.tag_id == self.id,
            Post.status == 'published'
        ).count()
    
    @property
    def url(self):
        """Get tag URL"""
        from app.utils.tenant import get_current_tenant
        tenant = get_current_tenant()
        if tenant:
            return f"https://{tenant.full_domain}/tag/{self.slug}"
        return f"/tag/{self.slug}"
    
    def to_dict(self):
        """Convert tag to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'color': self.color,
            'use_count': self.use_count,
            'post_count': self.post_count,
            'url': self.url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@event.listens_for(Category, 'before_insert')
def generate_category_slug(mapper, connection, target):
    """Generate slug before insert if not provided"""
    if not target.slug and target.name:
        import re
        slug = re.sub(r'[^a-zA-Z0-9\-_\s]', '', target.name.lower())
        slug = re.sub(r'[\s_]+', '-', slug).strip('-')
        target.slug = slug[:100]

@event.listens_for(Tag, 'before_insert')
def generate_tag_slug(mapper, connection, target):
    """Generate slug before insert if not provided"""
    if not target.slug and target.name:
        import re
        slug = re.sub(r'[^a-zA-Z0-9\-_\s]', '', target.name.lower())
        slug = re.sub(r'[\s_]+', '-', slug).strip('-')
        target.slug = slug[:50]
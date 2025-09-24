from datetime import datetime
from app import db
from app.utils.tenant import TenantMixin
from sqlalchemy import event

# Association table for post-tag many-to-many relationship
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Post(TenantMixin, db.Model):
    """Blog post model"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True, index=True)
    
    # Content
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, index=True)
    excerpt = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    
    # SEO
    meta_title = db.Column(db.String(200), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.String(255), nullable=True)
    
    # Media
    featured_image_url = db.Column(db.String(255), nullable=True)
    featured_image_alt = db.Column(db.String(200), nullable=True)
    
    # Status and visibility
    status = db.Column(db.String(20), default='draft', index=True)  # draft, published, private, scheduled
    is_featured = db.Column(db.Boolean, default=False, index=True)
    allow_comments = db.Column(db.Boolean, default=True)
    
    # Publishing
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    scheduled_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Stats
    view_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tags = db.relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    # Unique constraint for slug per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'slug', name='_tenant_slug_uc'),
    )
    
    def __repr__(self):
        return f'<Post {self.title}>'
    
    @property
    def is_published(self):
        """Check if post is published"""
        return (self.status == 'published' and 
                self.published_at and 
                self.published_at <= datetime.utcnow())
    
    @property
    def is_scheduled(self):
        """Check if post is scheduled"""
        return (self.status == 'scheduled' and 
                self.scheduled_at and 
                self.scheduled_at > datetime.utcnow())
    
    @property
    def url(self):
        """Get post URL"""
        from app.utils.tenant import get_current_tenant
        tenant = get_current_tenant()
        if tenant:
            return f"https://{tenant.full_domain}/post/{self.slug}"
        return f"/post/{self.slug}"
    
    @property
    def edit_url(self):
        """Get post edit URL"""
        return f"/dashboard/posts/{self.id}/edit"
    
    @property
    def reading_time(self):
        """Estimate reading time in minutes"""
        if not self.content:
            return 0
        
        # Average reading speed: 200-250 words per minute
        import re
        word_count = len(re.findall(r'\w+', self.content))
        return max(1, round(word_count / 225))
    
    def publish(self):
        """Publish the post"""
        self.status = 'published'
        if not self.published_at:
            self.published_at = datetime.utcnow()
    
    def unpublish(self):
        """Unpublish the post"""
        self.status = 'draft'
    
    def schedule(self, scheduled_at):
        """Schedule the post"""
        self.status = 'scheduled'
        self.scheduled_at = scheduled_at
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        db.session.commit()
    
    def get_excerpt(self, length=160):
        """Get excerpt with fallback to content"""
        if self.excerpt:
            return self.excerpt[:length] + '...' if len(self.excerpt) > length else self.excerpt
        
        # Extract text from HTML content
        import re
        text = re.sub('<[^<]+?>', '', self.content)
        return text[:length] + '...' if len(text) > length else text
    
    def to_dict(self):
        """Convert post to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.get_excerpt(),
            'content': self.content,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'featured_image_url': self.featured_image_url,
            'status': self.status,
            'is_featured': self.is_featured,
            'is_published': self.is_published,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'view_count': self.view_count,
            'comment_count': self.comment_count,
            'reading_time': self.reading_time,
            'url': self.url,
            'author': self.author.to_dict() if self.author else None,
            'category': self.category.to_dict() if self.category else None,
            'tags': [tag.to_dict() for tag in self.tags]
        }

@event.listens_for(Post, 'before_insert')
def generate_slug(mapper, connection, target):
    """Generate slug before insert if not provided"""
    if not target.slug and target.title:
        import re
        slug = re.sub(r'[^a-zA-Z0-9\-_\s]', '', target.title.lower())
        slug = re.sub(r'[\s_]+', '-', slug).strip('-')
        target.slug = slug[:200]  # Limit slug length
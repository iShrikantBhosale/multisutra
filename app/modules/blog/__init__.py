"""
Blog Module - Handles public blog functionality, posts display, and content management
Modular design inspired by Astro's approach
"""

from flask import Blueprint, request, render_template, abort, jsonify
from sqlalchemy import desc, or_
from datetime import datetime

from app import db
from app.models import Post, Category, Tag, Comment

class BlogModule:
    """Blog module for public-facing blog functionality"""
    
    def __init__(self):
        self.blueprint = Blueprint('blog', __name__)
        self._register_routes()
    
    def _register_routes(self):
        """Register all blog routes"""
        self.blueprint.add_url_rule('/', 'index', self.index)
        self.blueprint.add_url_rule('/post/<slug>', 'post', self.post)
        self.blueprint.add_url_rule('/category/<slug>', 'category', self.category)
        self.blueprint.add_url_rule('/tag/<slug>', 'tag', self.tag)
        self.blueprint.add_url_rule('/search', 'search', self.search)
        self.blueprint.add_url_rule('/feed.xml', 'rss_feed', self.rss_feed)
        self.blueprint.add_url_rule('/sitemap.xml', 'sitemap', self.sitemap)
    
    def index(self):
        """Homepage with recent posts"""
        page = request.args.get('page', 1, type=int)
        per_page = 6  # Number of posts per page
        
        posts_query = Post.query.filter_by(status='published').order_by(desc(Post.published_at))
        posts = posts_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get featured post
        featured_post = Post.query.filter_by(
            status='published', 
            is_featured=True
        ).order_by(desc(Post.published_at)).first()
        
        # Get categories for navigation
        categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
        
        # Get recent posts for sidebar
        recent_posts = Post.query.filter_by(status='published').order_by(
            desc(Post.published_at)
        ).limit(5).all()
        
        return render_template('components/blog/index.html',
                             posts=posts,
                             featured_post=featured_post,
                             categories=categories,
                             recent_posts=recent_posts)
    
    def post(self, slug):
        """Individual post page"""
        post = Post.query.filter_by(slug=slug, status='published').first_or_404()
        
        # Increment view count
        post.increment_view_count()
        
        # Get related posts (same category, excluding current post)
        related_posts = Post.query.filter(
            Post.category_id == post.category_id,
            Post.id != post.id,
            Post.status == 'published'
        ).order_by(desc(Post.published_at)).limit(3).all()
        
        # Get approved comments
        comments = Comment.query.filter_by(
            post_id=post.id,
            is_approved=True
        ).order_by(Comment.created_at).all()
        
        return render_template('components/blog/post.html',
                             post=post,
                             related_posts=related_posts,
                             comments=comments)
    
    def category(self, slug):
        """Category page with posts"""
        category = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
        
        page = request.args.get('page', 1, type=int)
        per_page = 6
        
        posts = Post.query.filter_by(
            category_id=category.id,
            status='published'
        ).order_by(desc(Post.published_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('components/blog/category.html',
                             category=category,
                             posts=posts)
    
    def tag(self, slug):
        """Tag page with posts"""
        tag = Tag.query.filter_by(slug=slug).first_or_404()
        
        page = request.args.get('page', 1, type=int)
        per_page = 6
        
        posts = Post.query.filter(
            Post.tags.contains(tag),
            Post.status == 'published'
        ).order_by(desc(Post.published_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('components/blog/tag.html',
                             tag=tag,
                             posts=posts)
    
    def search(self):
        """Search posts"""
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 6
        
        posts = None
        if query:
            # Search in title, content, and excerpt
            posts = Post.query.filter(
                Post.status == 'published',
                or_(
                    Post.title.contains(query),
                    Post.content.contains(query),
                    Post.excerpt.contains(query)
                )
            ).order_by(desc(Post.published_at)).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        return render_template('components/blog/search.html',
                             query=query,
                             posts=posts)
    
    def rss_feed(self):
        """Generate RSS feed"""
        posts = Post.query.filter_by(status='published').order_by(
            desc(Post.published_at)
        ).limit(20).all()
        
        response = render_template('components/blog/rss.xml', posts=posts)
        response = response.replace('&', '&amp;')  # Basic XML escaping
        
        from flask import Response
        return Response(response, mimetype='application/rss+xml')
    
    def sitemap(self):
        """Generate XML sitemap"""
        posts = Post.query.filter_by(status='published').all()
        categories = Category.query.filter_by(is_active=True).all()
        tags = Tag.query.all()
        
        from flask import Response
        response = render_template('components/blog/sitemap.xml',
                                 posts=posts,
                                 categories=categories,
                                 tags=tags)
        
        return Response(response, mimetype='application/xml')
    
    def get_blog_stats(self):
        """Get blog statistics for dashboard"""
        return {
            'total_posts': Post.query.filter_by(status='published').count(),
            'total_drafts': Post.query.filter_by(status='draft').count(),
            'total_categories': Category.query.filter_by(is_active=True).count(),
            'total_comments': Comment.query.filter_by(is_approved=True).count(),
            'total_views': db.session.query(db.func.sum(Post.view_count)).scalar() or 0
        }
    
    def get_recent_posts(self, limit=5):
        """Get recent published posts"""
        return Post.query.filter_by(status='published').order_by(
            desc(Post.published_at)
        ).limit(limit).all()
    
    def get_popular_posts(self, limit=5):
        """Get popular posts by view count"""
        return Post.query.filter_by(status='published').order_by(
            desc(Post.view_count)
        ).limit(limit).all()

# Create module instance
blog_module = BlogModule()
from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.tenant import get_current_tenant, tenant_required
from app.models import Post, Category, Tag
from app import db, cache
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/health')
def health_check():
    """Health check endpoint for deployment platforms"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'multisutra-cms'
    }), 200

@bp.route('/setup', methods=['GET', 'POST'])
def quick_setup():
    """Quick setup for first-time deployment - works without existing tenant"""
    from app.models.tenant import Tenant
    from app.models.user import User
    
    if request.method == 'POST':
        # Create default tenant if it doesn't exist
        tenant = Tenant.query.filter_by(subdomain='main').first()
        if not tenant:
            tenant = Tenant(
                name='MultiSutra Blog',
                subdomain='main',
                domain=request.host,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(tenant)
            db.session.commit()
        
        # Create admin user
        email = request.form.get('email', 'admin@example.com')
        password = request.form.get('password', 'admin123')
        
        existing_user = User.for_tenant(tenant.id).filter_by(email=email).first()
        if not existing_user:
            admin_user = User(
                email=email,
                username='admin',
                first_name='Admin',
                last_name='User',
                tenant_id=tenant.id,
                role='admin',
                is_active=True
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            
            return jsonify({
                'message': 'Setup completed successfully!',
                'tenant': tenant.name,
                'login_url': url_for('auth.login'),
                'dashboard_url': url_for('dashboard.index'),
                'email': email
            })
        else:
            return jsonify({'message': 'Setup already completed', 'login_url': url_for('auth.login')})
    
    return '''
    <html>
    <head><title>MultiSutra CMS - Quick Setup</title></head>
    <body style="font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px;">
        <h1>🚀 MultiSutra CMS Setup</h1>
        <p>Set up your blog and admin account:</p>
        <form method="POST">
            <div style="margin-bottom: 15px;">
                <label>Admin Email:</label><br>
                <input type="email" name="email" value="admin@example.com" required style="width: 100%; padding: 8px; margin-top: 5px;">
            </div>
            <div style="margin-bottom: 15px;">
                <label>Admin Password:</label><br>
                <input type="password" name="password" value="admin123" required style="width: 100%; padding: 8px; margin-top: 5px;">
            </div>
            <button type="submit" style="background: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer;">
                Create Blog & Admin Account
            </button>
        </form>
        <p style="margin-top: 30px; color: #666; font-size: 14px;">
            After setup, you can access:<br>
            • <a href="/auth/login">Login Page</a><br>
            • <a href="/dashboard/">Dashboard</a>
        </p>
    </body>
    </html>
    '''

@bp.before_app_request
def before_request():
    """Set tenant context for each request"""
    # This will automatically set the tenant based on subdomain
    get_current_tenant()

@bp.route('/')
def index():
    """Homepage - shows recent posts for the tenant"""
    tenant = get_current_tenant()
    
    if not tenant:
        # Main domain - show tenant selection or landing page
        return render_template('main/landing.html')
    
    # Get published posts for this tenant
    page = request.args.get('page', 1, type=int)
    posts_per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    
    posts = Post.for_tenant(tenant.id).filter_by(status='published')\
                .order_by(Post.published_at.desc())\
                .paginate(page=page, per_page=posts_per_page, error_out=False)
    
    # Get featured posts
    featured_posts = Post.for_tenant(tenant.id)\
                        .filter_by(status='published', is_featured=True)\
                        .order_by(Post.published_at.desc()).limit(3).all()
    
    # Get recent categories with post counts
    categories = Category.for_tenant(tenant.id).filter_by(is_active=True)\
                        .order_by(Category.sort_order, Category.name).all()
    
    return render_template('main/index.html',
                         tenant=tenant,
                         posts=posts,
                         featured_posts=featured_posts,
                         categories=categories)

@bp.route('/post/<slug>')
@tenant_required
def post_detail(slug):
    """Post detail page"""
    tenant = get_current_tenant()
    
    post = Post.for_tenant(tenant.id).filter_by(slug=slug, status='published').first_or_404()
    
    # Increment view count
    post.increment_view_count()
    
    # Get related posts (same category, excluding current post)
    related_posts = []
    if post.category:
        related_posts = Post.for_tenant(tenant.id)\
                           .filter(Post.category_id == post.category.id,
                                 Post.id != post.id,
                                 Post.status == 'published')\
                           .order_by(Post.published_at.desc()).limit(3).all()
    
    return render_template('main/post_detail.html',
                         tenant=tenant,
                         post=post,
                         related_posts=related_posts)

@bp.route('/category/<slug>')
@tenant_required
def category_posts(slug):
    """Posts in a specific category"""
    tenant = get_current_tenant()
    
    category = Category.for_tenant(tenant.id).filter_by(slug=slug, is_active=True).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    posts_per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    
    posts = Post.for_tenant(tenant.id).filter_by(category=category, status='published')\
                .order_by(Post.published_at.desc())\
                .paginate(page=page, per_page=posts_per_page, error_out=False)
    
    return render_template('main/category_posts.html',
                         tenant=tenant,
                         category=category,
                         posts=posts)

@bp.route('/tag/<slug>')
@tenant_required
def tag_posts(slug):
    """Posts with a specific tag"""
    tenant = get_current_tenant()
    
    tag = Tag.for_tenant(tenant.id).filter_by(slug=slug).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    posts_per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    
    posts = Post.for_tenant(tenant.id).filter(Post.tags.contains(tag), Post.status == 'published')\
                .order_by(Post.published_at.desc())\
                .paginate(page=page, per_page=posts_per_page, error_out=False)
    
    return render_template('main/tag_posts.html',
                         tenant=tenant,
                         tag=tag,
                         posts=posts)

@bp.route('/search')
@tenant_required
def search():
    """Search posts"""
    tenant = get_current_tenant()
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('main/search.html', tenant=tenant, query=query, posts=None)
    
    page = request.args.get('page', 1, type=int)
    posts_per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    
    # Simple search in title and content
    posts = Post.for_tenant(tenant.id)\
                .filter(db.or_(
                    Post.title.contains(query),
                    Post.content.contains(query),
                    Post.excerpt.contains(query)
                ), Post.status == 'published')\
                .order_by(Post.published_at.desc())\
                .paginate(page=page, per_page=posts_per_page, error_out=False)
    
    return render_template('main/search.html',
                         tenant=tenant,
                         query=query,
                         posts=posts)

@bp.route('/archive')
@tenant_required
def archive():
    """Post archive by date"""
    tenant = get_current_tenant()
    
    # Get posts grouped by year and month
    posts_by_date = db.session.query(
        db.extract('year', Post.published_at).label('year'),
        db.extract('month', Post.published_at).label('month'),
        db.func.count(Post.id).label('count')
    ).filter(
        Post.tenant_id == tenant.id,
        Post.status == 'published'
    ).group_by('year', 'month').order_by('year desc', 'month desc').all()
    
    return render_template('main/archive.html',
                         tenant=tenant,
                         posts_by_date=posts_by_date)

@bp.route('/archive/<int:year>/<int:month>')
@tenant_required
def archive_posts(year, month):
    """Posts for a specific month"""
    tenant = get_current_tenant()
    
    page = request.args.get('page', 1, type=int)
    posts_per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    
    posts = Post.for_tenant(tenant.id)\
                .filter(db.extract('year', Post.published_at) == year,
                       db.extract('month', Post.published_at) == month,
                       Post.status == 'published')\
                .order_by(Post.published_at.desc())\
                .paginate(page=page, per_page=posts_per_page, error_out=False)
    
    return render_template('main/archive_posts.html',
                         tenant=tenant,
                         posts=posts,
                         year=year,
                         month=month)

@bp.route('/sitemap.xml')
@tenant_required
def sitemap():
    """Generate XML sitemap for the tenant"""
    tenant = get_current_tenant()
    
    # Get all published posts
    posts = Post.for_tenant(tenant.id).filter_by(status='published')\
                .order_by(Post.published_at.desc()).all()
    
    # Get all active categories
    categories = Category.for_tenant(tenant.id).filter_by(is_active=True).all()
    
    # Get all tags with posts
    tags = Tag.for_tenant(tenant.id).join(Post.tags)\
              .filter(Post.status == 'published').distinct().all()
    
    return render_template('main/sitemap.xml',
                         tenant=tenant,
                         posts=posts,
                         categories=categories,
                         tags=tags), 200, {'Content-Type': 'application/xml'}

@bp.route('/robots.txt')
@tenant_required
def robots():
    """Generate robots.txt for the tenant"""
    tenant = get_current_tenant()
    
    return render_template('main/robots.txt', tenant=tenant), 200, {'Content-Type': 'text/plain'}

@bp.route('/feed.xml')
@tenant_required
def rss_feed():
    """Generate RSS feed for the tenant"""
    tenant = get_current_tenant()
    
    # Get recent published posts
    posts = Post.for_tenant(tenant.id).filter_by(status='published')\
                .order_by(Post.published_at.desc()).limit(20).all()
    
    return render_template('main/feed.xml',
                         tenant=tenant,
                         posts=posts), 200, {'Content-Type': 'application/rss+xml'}
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import Post, Category, Tag, MediaFile, Comment, User
from app.utils.tenant import get_current_tenant, tenant_required
from app import db

bp = Blueprint('api', __name__)

@bp.before_request
@login_required
@tenant_required
def before_request():
    """Ensure user is logged in and tenant exists"""
    pass

@bp.route('/posts')
def get_posts():
    """Get posts API"""
    tenant = get_current_tenant()
    
    # Apply filters
    status = request.args.get('status', 'published')
    limit = min(request.args.get('limit', 10, type=int), 100)
    offset = request.args.get('offset', 0, type=int)
    
    posts_query = Post.for_tenant().filter_by(status=status)\
                     .order_by(Post.published_at.desc())
    
    posts = posts_query.offset(offset).limit(limit).all()
    total = posts_query.count()
    
    return jsonify({
        'posts': [post.to_dict() for post in posts],
        'total': total,
        'limit': limit,
        'offset': offset
    })

@bp.route('/posts/<int:id>')
def get_post(id):
    """Get single post API"""
    tenant = get_current_tenant()
    
    post = Post.for_tenant().filter_by(id=id).first()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    # Check permissions
    if post.status != 'published' and not current_user.can_edit_post(post):
        return jsonify({'error': 'Post not found'}), 404
    
    return jsonify({'post': post.to_dict()})

@bp.route('/categories')
def get_categories():
    """Get categories API"""
    tenant = get_current_tenant()
    
    categories = Category.for_tenant().filter_by(is_active=True)\
                        .order_by(Category.sort_order, Category.name).all()
    
    return jsonify({
        'categories': [category.to_dict() for category in categories]
    })

@bp.route('/tags')
def get_tags():
    """Get tags API"""
    tenant = get_current_tenant()
    
    # Search tags
    search = request.args.get('q', '').strip()
    limit = min(request.args.get('limit', 20, type=int), 100)
    
    tags_query = Tag.for_tenant()
    
    if search:
        tags_query = tags_query.filter(Tag.name.contains(search))
    
    tags = tags_query.order_by(Tag.use_count.desc(), Tag.name)\
                    .limit(limit).all()
    
    return jsonify({
        'tags': [tag.to_dict() for tag in tags]
    })

@bp.route('/media')
def get_media():
    """Get media files API"""
    tenant = get_current_tenant()
    
    file_type = request.args.get('type')
    limit = min(request.args.get('limit', 20, type=int), 100)
    offset = request.args.get('offset', 0, type=int)
    
    media_query = MediaFile.for_tenant()
    
    if file_type:
        media_query = media_query.filter_by(file_type=file_type)
    
    media_files = media_query.order_by(MediaFile.created_at.desc())\
                            .offset(offset).limit(limit).all()
    
    total = media_query.count()
    
    return jsonify({
        'media_files': [media.to_dict() for media in media_files],
        'total': total,
        'limit': limit,
        'offset': offset
    })

@bp.route('/search')
def search():
    """Search API"""
    tenant = get_current_tenant()
    
    query = request.args.get('q', '').strip()
    content_type = request.args.get('type', 'posts')  # posts, categories, tags
    limit = min(request.args.get('limit', 10, type=int), 50)
    
    if not query:
        return jsonify({'results': [], 'total': 0})
    
    results = []
    total = 0
    
    if content_type == 'posts':
        posts = Post.for_tenant().filter(
            db.or_(
                Post.title.contains(query),
                Post.content.contains(query)
            ),
            Post.status == 'published'
        ).order_by(Post.published_at.desc()).limit(limit).all()
        
        results = [post.to_dict() for post in posts]
        total = len(results)
        
    elif content_type == 'categories':
        categories = Category.for_tenant().filter(
            Category.name.contains(query),
            Category.is_active == True
        ).order_by(Category.name).limit(limit).all()
        
        results = [category.to_dict() for category in categories]
        total = len(results)
        
    elif content_type == 'tags':
        tags = Tag.for_tenant().filter(
            Tag.name.contains(query)
        ).order_by(Tag.use_count.desc(), Tag.name).limit(limit).all()
        
        results = [tag.to_dict() for tag in tags]
        total = len(results)
    
    return jsonify({
        'results': results,
        'total': total,
        'query': query,
        'type': content_type
    })

@bp.route('/stats')
def get_stats():
    """Get statistics API"""
    tenant = get_current_tenant()
    
    # Only admins can view detailed stats
    if not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403
    
    # Get various statistics
    stats = {
        'posts': {
            'total': Post.for_tenant().count(),
            'published': Post.for_tenant().filter_by(status='published').count(),
            'drafts': Post.for_tenant().filter_by(status='draft').count(),
            'scheduled': Post.for_tenant().filter_by(status='scheduled').count(),
        },
        'categories': Category.for_tenant().count(),
        'tags': Tag.for_tenant().count(),
        'media_files': MediaFile.for_tenant().count(),
        'comments': {
            'total': Comment.for_tenant().count(),
            'approved': Comment.for_tenant().filter_by(is_approved=True).count(),
            'pending': Comment.for_tenant().filter_by(status='pending').count(),
        },
        'users': User.for_tenant().count(),
        'total_views': db.session.query(db.func.sum(Post.view_count))\
                                .filter(Post.tenant_id == tenant.id).scalar() or 0
    }
    
    return jsonify({'stats': stats})

@bp.route('/posts/<int:id>/toggle-featured', methods=['POST'])
def toggle_post_featured(id):
    """Toggle post featured status"""
    tenant = get_current_tenant()
    
    if not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403
    
    post = Post.for_tenant().filter_by(id=id).first()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    post.is_featured = not post.is_featured
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_featured': post.is_featured,
        'post_id': post.id
    })

@bp.route('/comments/<int:id>/approve', methods=['POST'])
def approve_comment(id):
    """Approve comment"""
    tenant = get_current_tenant()
    
    if not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403
    
    comment = Comment.for_tenant().filter_by(id=id).first()
    
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    comment.approve()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'status': comment.status,
        'comment_id': comment.id
    })

@bp.route('/comments/<int:id>/spam', methods=['POST'])
def mark_comment_spam(id):
    """Mark comment as spam"""
    tenant = get_current_tenant()
    
    if not current_user.is_admin():
        return jsonify({'error': 'Permission denied'}), 403
    
    comment = Comment.for_tenant().filter_by(id=id).first()
    
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    comment.mark_as_spam()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'status': comment.status,
        'comment_id': comment.id
    })
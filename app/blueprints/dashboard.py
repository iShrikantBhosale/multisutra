from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Post, Category, Tag, MediaFile, User, Comment
from app.utils.tenant import get_current_tenant, tenant_required
from app import db
from datetime import datetime
import os
from PIL import Image

bp = Blueprint('dashboard', __name__)

@bp.before_request
@login_required
@tenant_required
def before_request():
    """Ensure user is logged in and tenant exists"""
    pass

@bp.route('/')
def index():
    """Dashboard homepage"""
    tenant = get_current_tenant()
    
    # Get statistics
    total_posts = Post.for_tenant().count()
    published_posts = Post.for_tenant().filter_by(status='published').count()
    draft_posts = Post.for_tenant().filter_by(status='draft').count()
    total_views = db.session.query(db.func.sum(Post.view_count)).filter(
        Post.tenant_id == tenant.id).scalar() or 0
    
    # Get recent posts
    recent_posts = Post.for_tenant().order_by(Post.created_at.desc()).limit(5).all()
    
    # Get recent comments (if user is admin)
    recent_comments = []
    if current_user.is_admin():
        recent_comments = Comment.for_tenant().order_by(Comment.created_at.desc()).limit(5).all()
    
    return render_template('dashboard/index.html',
                         tenant=tenant,
                         stats={
                             'total_posts': total_posts,
                             'published_posts': published_posts,
                             'draft_posts': draft_posts,
                             'total_views': total_views
                         },
                         recent_posts=recent_posts,
                         recent_comments=recent_comments)

@bp.route('/posts')
def posts():
    """Posts management"""
    tenant = get_current_tenant()
    
    # Filter posts based on user role
    if current_user.is_admin():
        posts_query = Post.for_tenant()
    else:
        posts_query = Post.for_tenant().filter_by(author_id=current_user.id)
    
    # Apply filters
    status_filter = request.args.get('status')
    if status_filter:
        posts_query = posts_query.filter_by(status=status_filter)
    
    category_filter = request.args.get('category', type=int)
    if category_filter:
        posts_query = posts_query.filter_by(category_id=category_filter)
    
    # Search
    search = request.args.get('search', '').strip()
    if search:
        posts_query = posts_query.filter(Post.title.contains(search))
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    posts_per_page = current_app.config.get('ADMIN_POSTS_PER_PAGE', 20)
    
    posts = posts_query.order_by(Post.created_at.desc())\
                      .paginate(page=page, per_page=posts_per_page, error_out=False)
    
    # Get categories for filter
    categories = Category.for_tenant().filter_by(is_active=True).all()
    
    return render_template('dashboard/posts.html',
                         tenant=tenant,
                         posts=posts,
                         categories=categories,
                         current_status=status_filter,
                         current_category=category_filter,
                         search_query=search)

@bp.route('/posts/new', methods=['GET', 'POST'])
def new_post():
    """Create new post"""
    tenant = get_current_tenant()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        excerpt = request.form.get('excerpt', '').strip()
        category_id = request.form.get('category_id', type=int)
        tags_input = request.form.get('tags', '').strip()
        status = request.form.get('status', 'draft')
        is_featured = bool(request.form.get('is_featured'))
        
        # SEO fields
        meta_title = request.form.get('meta_title', '').strip()
        meta_description = request.form.get('meta_description', '').strip()
        meta_keywords = request.form.get('meta_keywords', '').strip()
        
        # Featured image
        featured_image_url = request.form.get('featured_image_url', '').strip()
        featured_image_alt = request.form.get('featured_image_alt', '').strip()
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return redirect(url_for('dashboard.new_post'))
        
        # Create post
        post = Post(
            tenant_id=tenant.id,
            author_id=current_user.id,
            title=title,
            content=content,
            excerpt=excerpt,
            category_id=category_id if category_id > 0 else None,
            status=status,
            is_featured=is_featured,
            meta_title=meta_title,
            meta_description=meta_description,
            meta_keywords=meta_keywords,
            featured_image_url=featured_image_url,
            featured_image_alt=featured_image_alt
        )
        
        # Set published date if publishing
        if status == 'published':
            post.published_at = datetime.utcnow()
        
        db.session.add(post)
        db.session.flush()  # Get the post ID
        
        # Handle tags
        if tags_input:
            tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
            for tag_name in tag_names:
                # Find or create tag
                tag = Tag.for_tenant().filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(tenant_id=tenant.id, name=tag_name)
                    db.session.add(tag)
                post.tags.append(tag)
        
        db.session.commit()
        
        flash('Post created successfully!', 'success')
        return redirect(url_for('dashboard.edit_post', id=post.id))
    
    # GET request - show form
    categories = Category.for_tenant().filter_by(is_active=True)\
                       .order_by(Category.sort_order, Category.name).all()
    
    return render_template('dashboard/edit_post.html',
                         tenant=tenant,
                         post=None,
                         categories=categories,
                         is_new=True)

@bp.route('/posts/<int:id>/edit', methods=['GET', 'POST'])
def edit_post(id):
    """Edit existing post"""
    tenant = get_current_tenant()
    
    # Get post and check permissions
    post = Post.for_tenant().filter_by(id=id).first_or_404()
    
    if not current_user.can_edit_post(post):
        flash('You do not have permission to edit this post.', 'error')
        return redirect(url_for('dashboard.posts'))
    
    if request.method == 'POST':
        post.title = request.form.get('title', '').strip()
        post.content = request.form.get('content', '').strip()
        post.excerpt = request.form.get('excerpt', '').strip()
        
        category_id = request.form.get('category_id', type=int)
        post.category_id = category_id if category_id > 0 else None
        
        tags_input = request.form.get('tags', '').strip()
        status = request.form.get('status', 'draft')
        post.is_featured = bool(request.form.get('is_featured'))
        
        # SEO fields
        post.meta_title = request.form.get('meta_title', '').strip()
        post.meta_description = request.form.get('meta_description', '').strip()
        post.meta_keywords = request.form.get('meta_keywords', '').strip()
        
        # Featured image
        post.featured_image_url = request.form.get('featured_image_url', '').strip()
        post.featured_image_alt = request.form.get('featured_image_alt', '').strip()
        
        if not post.title or not post.content:
            flash('Title and content are required.', 'error')
            return redirect(url_for('dashboard.edit_post', id=id))
        
        # Update status and published date
        if status == 'published' and post.status != 'published':
            post.published_at = datetime.utcnow()
        post.status = status
        
        # Handle tags
        post.tags.clear()  # Remove existing tags
        if tags_input:
            tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
            for tag_name in tag_names:
                # Find or create tag
                tag = Tag.for_tenant().filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(tenant_id=tenant.id, name=tag_name)
                    db.session.add(tag)
                post.tags.append(tag)
        
        db.session.commit()
        
        flash('Post updated successfully!', 'success')
        return redirect(url_for('dashboard.edit_post', id=id))
    
    # GET request - show form
    categories = Category.for_tenant().filter_by(is_active=True)\
                       .order_by(Category.sort_order, Category.name).all()
    
    # Get current tags as comma-separated string
    current_tags = ', '.join([tag.name for tag in post.tags])
    
    return render_template('dashboard/edit_post.html',
                         tenant=tenant,
                         post=post,
                         categories=categories,
                         current_tags=current_tags,
                         is_new=False)

@bp.route('/posts/<int:id>/delete', methods=['POST'])
def delete_post(id):
    """Delete post"""
    tenant = get_current_tenant()
    
    post = Post.for_tenant().filter_by(id=id).first_or_404()
    
    if not current_user.can_delete_post(post):
        flash('You do not have permission to delete this post.', 'error')
        return redirect(url_for('dashboard.posts'))
    
    title = post.title
    db.session.delete(post)
    db.session.commit()
    
    flash(f'Post "{title}" has been deleted.', 'success')
    return redirect(url_for('dashboard.posts'))

@bp.route('/media')
def media():
    """Media library"""
    tenant = get_current_tenant()
    
    # Get media files for this tenant
    page = request.args.get('page', 1, type=int)
    file_type = request.args.get('type', '')
    
    media_query = MediaFile.for_tenant()
    
    if file_type:
        media_query = media_query.filter_by(file_type=file_type)
    
    media_files = media_query.order_by(MediaFile.created_at.desc())\
                            .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('dashboard/media.html',
                         tenant=tenant,
                         media_files=media_files,
                         current_type=file_type)

@bp.route('/media/upload', methods=['POST'])
def upload_media():
    """Upload media file"""
    tenant = get_current_tenant()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file extension
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    if not ('.' in file.filename and 
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Generate secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        # Create tenant-specific directory
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                str(tenant.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        mime_type = file.content_type or 'application/octet-stream'
        file_type = MediaFile.get_file_type(mime_type)
        
        # Get image dimensions if it's an image
        width = height = None
        if file_type == 'image':
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
            except Exception:
                pass
        
        # Create media file record
        media_file = MediaFile(
            tenant_id=tenant.id,
            uploaded_by=current_user.id,
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_url=f'/static/uploads/{tenant.id}/{filename}',
            file_size=file_size,
            mime_type=mime_type,
            file_type=file_type,
            width=width,
            height=height
        )
        
        db.session.add(media_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'file': media_file.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/categories')
def categories():
    """Categories management"""
    tenant = get_current_tenant()
    
    if not current_user.is_admin():
        flash('You do not have permission to manage categories.', 'error')
        return redirect(url_for('dashboard.index'))
    
    categories = Category.for_tenant().order_by(Category.sort_order, Category.name).all()
    
    return render_template('dashboard/categories.html',
                         tenant=tenant,
                         categories=categories)

@bp.route('/users')
def users():
    """Users management (admin only)"""
    tenant = get_current_tenant()
    
    if not current_user.is_admin():
        flash('You do not have permission to manage users.', 'error')
        return redirect(url_for('dashboard.index'))
    
    users = User.for_tenant().order_by(User.created_at.desc()).all()
    
    return render_template('dashboard/users.html',
                         tenant=tenant,
                         users=users)

@bp.route('/settings')
def settings():
    """Tenant settings (admin only)"""
    tenant = get_current_tenant()
    
    if not current_user.is_admin():
        flash('You do not have permission to access settings.', 'error')
        return redirect(url_for('dashboard.index'))
    
    return render_template('dashboard/settings.html', tenant=tenant)
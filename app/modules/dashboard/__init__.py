"""
Dashboard Module - Handles admin dashboard, post management, and CMS functionality
Modular design inspired by Astro's approach
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import re

from app import db
from app.models import Post, Category, Tag, Comment, MediaFile, Setting

def slugify(text):
    """Simple slugify function"""
    # Convert to lowercase and replace spaces/special chars with dashes
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

class DashboardModule:
    """Dashboard module for CMS functionality"""
    
    def __init__(self):
        self.blueprint = Blueprint('dashboard', __name__)
        self._register_routes()
    
    def _register_routes(self):
        """Register all dashboard routes"""
        # Main dashboard
        self.blueprint.add_url_rule('/', 'index', self.index)
        
        # Post management
        self.blueprint.add_url_rule('/posts', 'posts', self.posts)
        self.blueprint.add_url_rule('/posts/new', 'new_post', self.new_post, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/posts/<int:id>/edit', 'edit_post', self.edit_post, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/posts/<int:id>/delete', 'delete_post', self.delete_post, methods=['POST'])
        
        # Category management
        self.blueprint.add_url_rule('/categories', 'categories', self.categories, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/categories/<int:id>/delete', 'delete_category', self.delete_category, methods=['POST'])
        
        # Media management
        self.blueprint.add_url_rule('/media', 'media', self.media, methods=['GET', 'POST'])
        self.blueprint.add_url_rule('/media/upload', 'upload_media', self.upload_media, methods=['POST'])
        self.blueprint.add_url_rule('/media/<int:id>/delete', 'delete_media', self.delete_media, methods=['POST'])
        
        # Comments management
        self.blueprint.add_url_rule('/comments', 'comments', self.comments)
        self.blueprint.add_url_rule('/comments/<int:id>/approve', 'approve_comment', self.approve_comment, methods=['POST'])
        self.blueprint.add_url_rule('/comments/<int:id>/delete', 'delete_comment', self.delete_comment, methods=['POST'])
        
        # Settings
        self.blueprint.add_url_rule('/settings', 'settings', self.settings, methods=['GET', 'POST'])
    
    @login_required
    def index(self):
        """Dashboard homepage"""
        # Get statistics
        stats = self._get_dashboard_stats()
        
        # Get recent posts
        recent_posts = Post.query.order_by(Post.updated_at.desc()).limit(5).all()
        
        # Get recent comments
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
        
        return render_template('components/dashboard/index.html',
                             stats=stats,
                             recent_posts=recent_posts,
                             recent_comments=recent_comments)
    
    @login_required
    def posts(self):
        """Posts management page"""
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        
        query = Post.query
        if status != 'all':
            query = query.filter_by(status=status)
        
        posts = query.order_by(Post.updated_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        
        return render_template('components/dashboard/posts.html',
                             posts=posts,
                             current_status=status)
    
    @login_required
    def new_post(self):
        """Create new post"""
        if request.method == 'POST':
            result = self._save_post(None, request.form)
            if result['success']:
                flash('Post created successfully!', 'success')
                return redirect(url_for('dashboard.edit_post', id=result['post'].id))
            else:
                flash(result['message'], 'error')
        
        categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
        return render_template('components/dashboard/edit_post.html',
                             post=None,
                             categories=categories,
                             is_new=True)
    
    @login_required
    def edit_post(self, id):
        """Edit existing post"""
        post = Post.query.get_or_404(id)
        
        if request.method == 'POST':
            result = self._save_post(post, request.form)
            if result['success']:
                flash('Post updated successfully!', 'success')
                return redirect(url_for('dashboard.edit_post', id=id))
            else:
                flash(result['message'], 'error')
        
        categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
        current_tags = ', '.join([tag.name for tag in post.tags])
        
        return render_template('components/dashboard/edit_post.html',
                             post=post,
                             categories=categories,
                             current_tags=current_tags,
                             is_new=False)
    
    @login_required
    def delete_post(self, id):
        """Delete post"""
        post = Post.query.get_or_404(id)
        
        try:
            db.session.delete(post)
            db.session.commit()
            flash('Post deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting post.', 'error')
        
        return redirect(url_for('dashboard.posts'))
    
    @login_required
    def categories(self):
        """Category management"""
        if request.method == 'POST':
            result = self._save_category(request.form)
            if result['success']:
                flash('Category saved successfully!', 'success')
            else:
                flash(result['message'], 'error')
            return redirect(url_for('dashboard.categories'))
        
        categories = Category.query.order_by(Category.sort_order, Category.name).all()
        return render_template('components/dashboard/categories.html',
                             categories=categories)
    
    @login_required
    def delete_category(self, id):
        """Delete category"""
        category = Category.query.get_or_404(id)
        
        try:
            # Update posts in this category to uncategorized
            Post.query.filter_by(category_id=id).update({'category_id': None})
            db.session.delete(category)
            db.session.commit()
            flash('Category deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting category.', 'error')
        
        return redirect(url_for('dashboard.categories'))
    
    @login_required
    def media(self):
        """Media library"""
        page = request.args.get('page', 1, type=int)
        
        media_files = MediaFile.query.order_by(MediaFile.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('components/dashboard/media.html',
                             media_files=media_files)
    
    @login_required
    def upload_media(self):
        """Handle media upload"""
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file selected'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
        
        result = self._save_uploaded_file(file)
        return jsonify(result)
    
    @login_required
    def delete_media(self, id):
        """Delete media file"""
        media_file = MediaFile.query.get_or_404(id)
        
        try:
            # Delete physical file
            if os.path.exists(media_file.file_path):
                os.remove(media_file.file_path)
            
            db.session.delete(media_file)
            db.session.commit()
            flash('Media file deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting media file.', 'error')
        
        return redirect(url_for('dashboard.media'))
    
    @login_required
    def comments(self):
        """Comments management"""
        status = request.args.get('status', 'pending')
        page = request.args.get('page', 1, type=int)
        
        query = Comment.query
        if status == 'pending':
            query = query.filter_by(is_approved=False)
        elif status == 'approved':
            query = query.filter_by(is_approved=True)
        
        comments = query.order_by(Comment.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
        
        return render_template('components/dashboard/comments.html',
                             comments=comments,
                             current_status=status)
    
    @login_required
    def approve_comment(self, id):
        """Approve comment"""
        comment = Comment.query.get_or_404(id)
        comment.is_approved = not comment.is_approved
        
        try:
            db.session.commit()
            status = 'approved' if comment.is_approved else 'rejected'
            flash(f'Comment {status} successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating comment.', 'error')
        
        return redirect(url_for('dashboard.comments'))
    
    @login_required
    def delete_comment(self, id):
        """Delete comment"""
        comment = Comment.query.get_or_404(id)
        
        try:
            db.session.delete(comment)
            db.session.commit()
            flash('Comment deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting comment.', 'error')
        
        return redirect(url_for('dashboard.comments'))
    
    @login_required
    def settings(self):
        """Blog settings"""
        if request.method == 'POST':
            result = self._save_settings(request.form)
            if result['success']:
                flash('Settings saved successfully!', 'success')
            else:
                flash(result['message'], 'error')
            return redirect(url_for('dashboard.settings'))
        
        # Get current settings
        settings = {}
        for setting in Setting.query.all():
            settings[setting.key] = setting.value
        
        return render_template('components/dashboard/settings.html',
                             settings=settings)
    
    def _get_dashboard_stats(self):
        """Get dashboard statistics"""
        return {
            'total_posts': Post.query.count(),
            'published_posts': Post.query.filter_by(status='published').count(),
            'draft_posts': Post.query.filter_by(status='draft').count(),
            'total_categories': Category.query.count(),
            'total_comments': Comment.query.count(),
            'pending_comments': Comment.query.filter_by(is_approved=False).count(),
            'total_media': MediaFile.query.count(),
            'total_views': db.session.query(db.func.sum(Post.view_count)).scalar() or 0
        }
    
    def _save_post(self, post, form_data):
        """Save post data"""
        try:
            is_new = post is None
            if is_new:
                post = Post()
                post.author_id = current_user.id
            
            # Basic fields
            post.title = form_data.get('title', '').strip()
            post.content = form_data.get('content', '').strip()
            post.excerpt = form_data.get('excerpt', '').strip()
            post.featured_image_url = form_data.get('featured_image_url', '').strip()
            post.status = form_data.get('status', 'draft')
            post.is_featured = bool(form_data.get('is_featured'))
            
            # SEO fields
            post.meta_title = form_data.get('meta_title', '').strip()
            post.meta_description = form_data.get('meta_description', '').strip()
            post.meta_keywords = form_data.get('meta_keywords', '').strip()
            
            # Generate slug
            if not post.slug or is_new:
                post.slug = slugify(post.title)
            
            # Set category
            category_id = form_data.get('category_id')
            if category_id and category_id.isdigit():
                post.category_id = int(category_id)
            
            # Set published date
            if post.status == 'published' and not post.published_at:
                post.published_at = datetime.utcnow()
            
            post.updated_at = datetime.utcnow()
            
            if is_new:
                db.session.add(post)
            
            # Handle tags
            self._update_post_tags(post, form_data.get('tags', ''))
            
            db.session.commit()
            return {'success': True, 'post': post}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error saving post: {str(e)}'}
    
    def _update_post_tags(self, post, tags_string):
        """Update post tags"""
        # Clear existing tags
        post.tags.clear()
        
        if tags_string:
            tag_names = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name, slug=slugify(tag_name))
                    db.session.add(tag)
                post.tags.append(tag)
    
    def _save_category(self, form_data):
        """Save category data"""
        try:
            category = Category(
                name=form_data.get('name', '').strip(),
                description=form_data.get('description', '').strip(),
                color=form_data.get('color', '#007bff'),
                sort_order=int(form_data.get('sort_order', 0) or 0)
            )
            category.slug = slugify(category.name)
            
            db.session.add(category)
            db.session.commit()
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': f'Error saving category: {str(e)}'}
    
    def _save_uploaded_file(self, file):
        """Save uploaded file"""
        try:
            # Create media file record
            media_file = MediaFile(
                filename=file.filename,
                original_filename=file.filename,
                file_path='',  # Will be set after saving
                file_size=0,   # Will be calculated
                mime_type=file.content_type,
                uploaded_by_id=current_user.id
            )
            
            # Save file (implementation depends on your storage setup)
            # For now, return a placeholder
            return {'success': True, 'media_file': media_file}
            
        except Exception as e:
            return {'success': False, 'message': f'Error uploading file: {str(e)}'}
    
    def _save_settings(self, form_data):
        """Save blog settings"""
        try:
            settings_to_save = [
                'blog_title', 'blog_description', 'blog_keywords',
                'posts_per_page', 'enable_comments', 'moderate_comments'
            ]
            
            for key in settings_to_save:
                value = form_data.get(key, '')
                Setting.set_value(key, value)
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'message': f'Error saving settings: {str(e)}'}

# Create module instance
dashboard_module = DashboardModule()
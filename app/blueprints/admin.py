from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import Tenant, User, Post, Category, Tag, Setting
from app import db
from werkzeug.security import generate_password_hash
import os

bp = Blueprint('admin', __name__)

@bp.before_request
@login_required
def before_request():
    """Ensure user is logged in"""
    # Check if user is super admin (you might want to implement this differently)
    if not getattr(current_user, 'is_super_admin', False):
        # For now, we'll check if user email is in a list of super admins
        super_admins = os.environ.get('SUPER_ADMINS', '').split(',')
        if current_user.email not in super_admins:
            flash('Access denied. Super admin privileges required.', 'error')
            return redirect(url_for('main.index'))

@bp.route('/')
def index():
    """Admin dashboard"""
    # Get system statistics
    total_tenants = Tenant.query.count()
    active_tenants = Tenant.query.filter_by(is_active=True).count()
    total_users = User.query.count()
    total_posts = Post.query.count()
    
    # Get recent tenants
    recent_tenants = Tenant.query.order_by(Tenant.created_at.desc()).limit(5).all()
    
    return render_template('admin/index.html',
                         stats={
                             'total_tenants': total_tenants,
                             'active_tenants': active_tenants,
                             'total_users': total_users,
                             'total_posts': total_posts
                         },
                         recent_tenants=recent_tenants)

@bp.route('/tenants')
def tenants():
    """Manage tenants"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status')  # active, inactive
    
    tenants_query = Tenant.query
    
    if search:
        tenants_query = tenants_query.filter(
            db.or_(
                Tenant.name.contains(search),
                Tenant.subdomain.contains(search),
                Tenant.title.contains(search)
            )
        )
    
    if status == 'active':
        tenants_query = tenants_query.filter_by(is_active=True)
    elif status == 'inactive':
        tenants_query = tenants_query.filter_by(is_active=False)
    
    tenants = tenants_query.order_by(Tenant.created_at.desc())\
                          .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/tenants.html',
                         tenants=tenants,
                         search_query=search,
                         current_status=status)

@bp.route('/tenants/new', methods=['GET', 'POST'])
def new_tenant():
    """Create new tenant"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subdomain = request.form.get('subdomain', '').strip().lower()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        # Admin user details
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_username = request.form.get('admin_username', '').strip()
        admin_password = request.form.get('admin_password', '').strip()
        
        # Validation
        errors = []
        
        if not name:
            errors.append('Tenant name is required.')
        
        if not subdomain:
            errors.append('Subdomain is required.')
        elif not subdomain.replace('-', '').replace('_', '').isalnum():
            errors.append('Subdomain must contain only letters, numbers, hyphens, and underscores.')
        elif Tenant.query.filter_by(subdomain=subdomain).first():
            errors.append('Subdomain is already taken.')
        
        if not admin_email or '@' not in admin_email:
            errors.append('Valid admin email is required.')
        
        if not admin_username:
            errors.append('Admin username is required.')
        
        if not admin_password or len(admin_password) < 6:
            errors.append('Admin password must be at least 6 characters long.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/edit_tenant.html', tenant=None, is_new=True)
        
        try:
            # Create tenant
            tenant = Tenant(
                name=name,
                subdomain=subdomain,
                title=title or name,
                description=description
            )
            db.session.add(tenant)
            db.session.flush()  # Get tenant ID
            
            # Create admin user for tenant
            admin_user = User(
                tenant_id=tenant.id,
                email=admin_email,
                username=admin_username,
                role='admin',
                is_active=True
            )
            admin_user.set_password(admin_password)
            
            db.session.add(admin_user)
            db.session.commit()
            
            flash(f'Tenant "{name}" created successfully!', 'success')
            return redirect(url_for('admin.tenants'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating tenant: {str(e)}', 'error')
    
    return render_template('admin/edit_tenant.html', tenant=None, is_new=True)

@bp.route('/tenants/<int:id>')
def tenant_detail(id):
    """View tenant details"""
    tenant = Tenant.query.get_or_404(id)
    
    # Get tenant statistics
    user_count = User.query.filter_by(tenant_id=tenant.id).count()
    post_count = Post.query.filter_by(tenant_id=tenant.id).count()
    published_posts = Post.query.filter_by(tenant_id=tenant.id, status='published').count()
    
    # Get recent users and posts
    recent_users = User.query.filter_by(tenant_id=tenant.id)\
                            .order_by(User.created_at.desc()).limit(5).all()
    
    recent_posts = Post.query.filter_by(tenant_id=tenant.id)\
                            .order_by(Post.created_at.desc()).limit(5).all()
    
    return render_template('admin/tenant_detail.html',
                         tenant=tenant,
                         stats={
                             'user_count': user_count,
                             'post_count': post_count,
                             'published_posts': published_posts
                         },
                         recent_users=recent_users,
                         recent_posts=recent_posts)

@bp.route('/tenants/<int:id>/edit', methods=['GET', 'POST'])
def edit_tenant(id):
    """Edit tenant"""
    tenant = Tenant.query.get_or_404(id)
    
    if request.method == 'POST':
        tenant.name = request.form.get('name', '').strip()
        tenant.title = request.form.get('title', '').strip()
        tenant.description = request.form.get('description', '').strip()
        tenant.theme = request.form.get('theme', 'default')
        tenant.is_active = bool(request.form.get('is_active'))
        
        # SEO settings
        tenant.meta_description = request.form.get('meta_description', '').strip()
        tenant.meta_keywords = request.form.get('meta_keywords', '').strip()
        tenant.google_analytics_id = request.form.get('google_analytics_id', '').strip()
        tenant.google_adsense_id = request.form.get('google_adsense_id', '').strip()
        
        # Social media
        tenant.facebook_url = request.form.get('facebook_url', '').strip()
        tenant.twitter_url = request.form.get('twitter_url', '').strip()
        tenant.instagram_url = request.form.get('instagram_url', '').strip()
        tenant.linkedin_url = request.form.get('linkedin_url', '').strip()
        
        try:
            db.session.commit()
            flash('Tenant updated successfully!', 'success')
            return redirect(url_for('admin.tenant_detail', id=tenant.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tenant: {str(e)}', 'error')
    
    return render_template('admin/edit_tenant.html', tenant=tenant, is_new=False)

@bp.route('/tenants/<int:id>/toggle-status', methods=['POST'])
def toggle_tenant_status(id):
    """Toggle tenant active status"""
    tenant = Tenant.query.get_or_404(id)
    
    tenant.is_active = not tenant.is_active
    db.session.commit()
    
    status = 'activated' if tenant.is_active else 'deactivated'
    flash(f'Tenant "{tenant.name}" has been {status}.', 'success')
    
    return redirect(url_for('admin.tenants'))

@bp.route('/tenants/<int:id>/delete', methods=['POST'])
def delete_tenant(id):
    """Delete tenant (dangerous operation)"""
    tenant = Tenant.query.get_or_404(id)
    
    # Get confirmation
    if request.form.get('confirm_name') != tenant.name:
        flash('Tenant name confirmation does not match.', 'error')
        return redirect(url_for('admin.tenant_detail', id=id))
    
    tenant_name = tenant.name
    
    try:
        # This will cascade delete all related data
        db.session.delete(tenant)
        db.session.commit()
        
        flash(f'Tenant "{tenant_name}" has been permanently deleted.', 'success')
        return redirect(url_for('admin.tenants'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting tenant: {str(e)}', 'error')
        return redirect(url_for('admin.tenant_detail', id=id))

@bp.route('/users')
def users():
    """Manage all users across tenants"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    tenant_id = request.args.get('tenant', type=int)
    role = request.args.get('role')
    
    users_query = User.query.join(Tenant)
    
    if search:
        users_query = users_query.filter(
            db.or_(
                User.email.contains(search),
                User.username.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    if tenant_id:
        users_query = users_query.filter_by(tenant_id=tenant_id)
    
    if role:
        users_query = users_query.filter_by(role=role)
    
    users = users_query.order_by(User.created_at.desc())\
                      .paginate(page=page, per_page=20, error_out=False)
    
    # Get tenants for filter
    tenants = Tenant.query.filter_by(is_active=True).order_by(Tenant.name).all()
    
    return render_template('admin/users.html',
                         users=users,
                         tenants=tenants,
                         search_query=search,
                         current_tenant=tenant_id,
                         current_role=role)

@bp.route('/system')
def system():
    """System settings and information"""
    import sys
    import platform
    
    system_info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'flask_env': os.environ.get('FLASK_ENV', 'production'),
        'database_url': os.environ.get('DATABASE_URL', 'Not configured'),
        'redis_url': os.environ.get('REDIS_URL', 'Not configured'),
    }
    
    return render_template('admin/system.html', system_info=system_info)
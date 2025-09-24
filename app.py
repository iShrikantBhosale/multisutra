import os
from app import create_app, db
from app.models import *
from flask_migrate import upgrade

app = create_app(os.environ.get('FLASK_ENV', 'development'))

@app.cli.command()
def init_db():
    """Initialize database with tables"""
    db.create_all()
    print("Database initialized!")

@app.cli.command()
def create_super_admin():
    """Create a super admin user"""
    from app.models import Tenant, User
    
    email = input("Enter super admin email: ").strip()
    password = input("Enter password: ").strip()
    
    if not email or not password:
        print("Email and password are required!")
        return
    
    # Create or get a default tenant for super admin
    tenant = Tenant.query.filter_by(subdomain='admin').first()
    if not tenant:
        tenant = Tenant(
            name='Admin',
            subdomain='admin',
            title='Admin Panel',
            description='Administrative tenant'
        )
        db.session.add(tenant)
        db.session.flush()
    
    # Create super admin user
    admin = User(
        tenant_id=tenant.id,
        email=email,
        username='superadmin',
        first_name='Super',
        last_name='Admin',
        role='admin'
    )
    admin.set_password(password)
    admin.is_super_admin = True  # Custom attribute for super admin
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"Super admin created: {email}")

@app.cli.command()
def seed_data():
    """Seed database with sample data"""
    from app.models import Tenant, User, Category, Post
    
    # Create sample tenant
    tenant = Tenant(
        name='Sample Blog',
        subdomain='demo',
        title='Demo Blog',
        description='A sample blog for demonstration'
    )
    db.session.add(tenant)
    db.session.flush()
    
    # Create admin user
    admin = User(
        tenant_id=tenant.id,
        email='admin@demo.blog',
        username='admin',
        first_name='Admin',
        last_name='User',
        role='admin'
    )
    admin.set_password('password123')
    db.session.add(admin)
    db.session.flush()
    
    # Create categories
    categories = [
        {'name': 'Technology', 'description': 'Tech-related posts'},
        {'name': 'Lifestyle', 'description': 'Lifestyle and personal posts'},
        {'name': 'Travel', 'description': 'Travel experiences and guides'},
    ]
    
    for cat_data in categories:
        category = Category(
            tenant_id=tenant.id,
            name=cat_data['name'],
            description=cat_data['description']
        )
        db.session.add(category)
    
    db.session.flush()
    
    # Create sample posts
    tech_category = Category.query.filter_by(name='Technology').first()
    
    posts = [
        {
            'title': 'Welcome to MultiSutra CMS',
            'content': '<p>This is a sample blog post created with MultiSutra CMS. The system supports rich text editing, media uploads, and much more!</p>',
            'status': 'published',
            'category': tech_category
        },
        {
            'title': 'Getting Started with Your Blog',
            'content': '<p>Here are some tips for getting started with your new blog powered by MultiSutra CMS.</p>',
            'status': 'published',
            'category': tech_category
        }
    ]
    
    for post_data in posts:
        post = Post(
            tenant_id=tenant.id,
            author_id=admin.id,
            title=post_data['title'],
            content=post_data['content'],
            status=post_data['status'],
            category=post_data['category'],
            published_at=db.func.now() if post_data['status'] == 'published' else None
        )
        db.session.add(post)
    
    db.session.commit()
    print(f"Sample data created for tenant: {tenant.subdomain}.{os.environ.get('MAIN_DOMAIN', 'multisutra.com')}")

if __name__ == '__main__':
    app.run(debug=True)
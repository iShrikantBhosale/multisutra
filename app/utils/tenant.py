from flask import request, g, current_app
from urllib.parse import urlparse
import threading

# Thread-local storage for tenant context
_local = threading.local()

def get_subdomain_from_request():
    """Extract subdomain from the current request"""
    if not request or not request.host:
        return None
        
    host = request.host.lower()
    
    # Remove port if present
    if ':' in host:
        host = host.split(':')[0]
    
    # Handle Render.com domains specially
    if '.onrender.com' in host:
        # For Render: app-name.onrender.com - no subdomain support
        # We'll treat the entire Render domain as the main site
        return 'main'  # Default tenant for Render deployments
    
    # Get main domain from config
    main_domain = current_app.config.get('MAIN_DOMAIN', 'localhost')
    
    # Check if it's a subdomain
    if host.endswith(f'.{main_domain}'):
        subdomain = host.replace(f'.{main_domain}', '')
        # Validate subdomain (basic validation)
        if subdomain and subdomain.replace('-', '').replace('_', '').isalnum():
            return subdomain
    elif host == main_domain or 'localhost' in host or 'onrender.com' in host:
        # Main domain, localhost, or Render - use default tenant
        return 'main'
    
    return None

def get_current_tenant():
    """Get the current tenant based on subdomain"""
    # Check thread-local storage first
    if hasattr(_local, 'tenant'):
        return _local.tenant
    
    # Check Flask's g object
    if hasattr(g, 'current_tenant'):
        return g.current_tenant
    
    subdomain = get_subdomain_from_request()
    if not subdomain:
        return None
    
    # Import here to avoid circular imports
    from app.models.tenant import Tenant
    tenant = Tenant.query.filter_by(subdomain=subdomain, is_active=True).first()
    
    # Cache in both thread-local and g
    _local.tenant = tenant
    g.current_tenant = tenant
    
    return tenant

def set_current_tenant(tenant):
    """Set the current tenant context"""
    _local.tenant = tenant
    g.current_tenant = tenant

def clear_tenant_context():
    """Clear tenant context"""
    if hasattr(_local, 'tenant'):
        delattr(_local, 'tenant')
    if hasattr(g, 'current_tenant'):
        delattr(g, 'current_tenant')

def require_tenant():
    """Decorator to require a valid tenant"""
    from functools import wraps
    from flask import abort
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            tenant = get_current_tenant()
            if not tenant:
                abort(404)  # Tenant not found
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def tenant_required(f):
    """Decorator that requires a tenant to be present"""
    from functools import wraps
    from flask import abort
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_tenant():
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

class TenantMixin:
    """Mixin class to add tenant filtering to models"""
    
    @classmethod
    def for_tenant(cls, tenant_id=None):
        """Filter query by tenant"""
        if tenant_id is None:
            tenant = get_current_tenant()
            if not tenant:
                # Return empty query if no tenant
                return cls.query.filter(cls.id == -1)
            tenant_id = tenant.id
        
        return cls.query.filter(cls.tenant_id == tenant_id)
    
    @classmethod
    def create_for_tenant(cls, **kwargs):
        """Create a new instance for the current tenant"""
        tenant = get_current_tenant()
        if not tenant:
            raise ValueError("No current tenant")
        
        kwargs['tenant_id'] = tenant.id
        return cls(**kwargs)
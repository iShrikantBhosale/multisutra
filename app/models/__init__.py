# Import all models to ensure they are registered with SQLAlchemy
from app.models.tenant import Tenant
from app.models.user import User
from app.models.post import Post
from app.models.category import Category, Tag
from app.models.media import MediaFile
from app.models.setting import Setting, Comment

__all__ = [
    'Tenant',
    'User', 
    'Post',
    'Category',
    'Tag',
    'MediaFile',
    'Setting',
    'Comment'
]
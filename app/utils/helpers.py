import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid
from flask import current_app

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_unique_filename(original_filename):
    """Generate unique filename while preserving extension"""
    name, ext = os.path.splitext(secure_filename(original_filename))
    unique_id = str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"

def optimize_image(image_path, max_width=1920, max_height=1080, quality=85):
    """Optimize image by resizing and compressing"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Calculate new dimensions
            width, height = img.size
            if width > max_width or height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save with optimization
            img.save(image_path, 'JPEG', quality=quality, optimize=True)
            
        return True
    except Exception as e:
        print(f"Error optimizing image {image_path}: {e}")
        return False

def create_thumbnail(image_path, thumbnail_path, size=(300, 300)):
    """Create thumbnail from image"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, 'JPEG', quality=80, optimize=True)
            
        return True
    except Exception as e:
        print(f"Error creating thumbnail {thumbnail_path}: {e}")
        return False

def get_file_size_formatted(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def sanitize_html(content):
    """Sanitize HTML content for safe display"""
    import bleach
    
    # Allowed tags and attributes for blog content
    allowed_tags = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'a', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre',
        'img', 'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'class'],
        'div': ['class'],
        'span': ['class'],
        'p': ['class'],
        'table': ['class'],
        'th': ['class'],
        'td': ['class'],
    }
    
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes)

def extract_excerpt(content, length=160):
    """Extract plain text excerpt from HTML content"""
    import re
    
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', content)
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    if len(text) <= length:
        return text
    
    # Try to break at word boundary
    excerpt = text[:length]
    last_space = excerpt.rfind(' ')
    if last_space > 0:
        excerpt = excerpt[:last_space]
    
    return excerpt + '...'
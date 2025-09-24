from datetime import datetime
from app import db
from app.utils.tenant import TenantMixin
import os

class MediaFile(TenantMixin, db.Model):
    """Media file model for uploads"""
    __tablename__ = 'media_files'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # Relative path
    file_url = db.Column(db.String(500), nullable=False)   # Full URL
    
    # File metadata
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=False)
    file_type = db.Column(db.String(20), nullable=False, index=True)  # image, video, document, etc.
    
    # Image-specific metadata
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    
    # File details
    title = db.Column(db.String(200), nullable=True)
    alt_text = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MediaFile {self.filename}>'
    
    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_type == 'image'
    
    @property
    def is_video(self):
        """Check if file is a video"""
        return self.file_type == 'video'
    
    @property
    def is_document(self):
        """Check if file is a document"""
        return self.file_type == 'document'
    
    @property
    def file_size_formatted(self):
        """Get formatted file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def dimensions(self):
        """Get image dimensions as string"""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return None
    
    def get_thumbnail_url(self, size='medium'):
        """Get thumbnail URL for images"""
        if not self.is_image:
            return None
        
        # For now, return the original URL
        # In production, you might want to generate actual thumbnails
        return self.file_url
    
    def delete_file(self):
        """Delete the physical file"""
        try:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
        except Exception as e:
            print(f"Error deleting file {self.file_path}: {e}")
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.last_used = datetime.utcnow()
    
    def to_dict(self):
        """Convert media file to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_url': self.file_url,
            'file_size': self.file_size,
            'file_size_formatted': self.file_size_formatted,
            'mime_type': self.mime_type,
            'file_type': self.file_type,
            'width': self.width,
            'height': self.height,
            'dimensions': self.dimensions,
            'title': self.title,
            'alt_text': self.alt_text,
            'description': self.description,
            'is_image': self.is_image,
            'is_video': self.is_video,
            'is_document': self.is_document,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploaded_by': self.uploaded_by_user.display_name if self.uploaded_by_user else None
        }

    @classmethod
    def get_file_type(cls, mime_type):
        """Determine file type from MIME type"""
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type in ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'application/vnd.ms-powerpoint',
                          'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
            return 'document'
        else:
            return 'other'